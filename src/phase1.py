"""Phase 1, Stage 1: does consumer sentiment improve forecasts of the severity and
persistence of financial stress beyond a stress-index baseline?

Implements PREREGISTRATION.md and PREREGISTRATION_ADDENDUM.md exactly. Do not change
settings here after results have been seen; add a dated addendum instead.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from data import load_real, make_synthetic

OUT = Path(__file__).resolve().parents[1] / "outputs"

# ---- registered settings -------------------------------------------------
EPISODE_THRESHOLD = 0.5
Z_WINDOW = 120            # 10-year rolling z-score of sentiment
MIN_TRAIN = 84
BLOCK, N_BOOT, SEED = 12, 1000, 0
R2_MIN = 0.02
FEATS_A = ["stress", "stress_chg3"]
FEATS_B = FEATS_A + ["sent_z", "sent_chg3"]
SPECS = [  # (name, outcome kind, horizon, primary?)
    ("Severity(3)", "severity", 3, True),
    ("Severity(6)", "severity", 6, False),
    ("Persistence(6)", "persistence", 6, False),
    ("Persistence(12)", "persistence", 12, False),
]


def build_features(sent, stress, z_window=Z_WINDOW):
    """Sentiment features are built on the full continuous sentiment history before merging."""
    sent = sent[sent.index >= "1978-01-01"].asfreq("MS")
    f = pd.DataFrame({"sent": sent})
    f["sent_z"] = (sent - sent.rolling(z_window).mean()) / sent.rolling(z_window).std()
    f["sent_chg3"] = sent.diff(3)
    df = pd.concat([f, stress.rename("stress")], axis=1).dropna()
    df["stress_chg3"] = stress.diff(3).reindex(df.index)
    return df.dropna()


def add_outcome(df, kind, h):
    fut = pd.concat([df.stress.shift(-k) for k in range(1, h + 1)], axis=1)
    ok = fut.notna().all(axis=1)
    if kind == "severity":
        y = fut.max(axis=1)
    else:
        y = (fut > EPISODE_THRESHOLD).sum(axis=1).astype(float)
    out = df.copy()
    out["y"] = y.where(ok)
    return out.dropna()


def _ols_predict(train, test, feats):
    X = np.column_stack([np.ones(len(train)), train[feats].to_numpy()])
    beta, *_ = np.linalg.lstsq(X, train["y"].to_numpy(), rcond=None)
    Xt = np.column_stack([np.ones(len(test)), test[feats].to_numpy()])
    return Xt @ beta


def oos_forecasts(df, h, min_train=MIN_TRAIN):
    """Expanding window, refit each January. Training rows need t' + h < January of the forecast year."""
    parts = []
    for yr in sorted(set(df.index.year)):
        test = df[df.index.year == yr]
        cutoff = pd.Timestamp(f"{yr}-01-01") - pd.DateOffset(months=h + 1)
        train = df[df.index <= cutoff]
        if len(train) < min_train or test.empty:
            continue
        parts.append(pd.DataFrame({"y": test["y"],
                                   "pA": _ols_predict(train, test, FEATS_A),
                                   "pB": _ols_predict(train, test, FEATS_B)}, index=test.index))
    if not parts:
        raise RuntimeError("Not enough history for out-of-sample forecasts.")
    return pd.concat(parts)


def oos_r2(res):
    mA, mB = ((res.y - res.pA) ** 2).mean(), ((res.y - res.pB) ** 2).mean()
    return 1 - mB / mA


def mae_pair(res):
    return (res.y - res.pA).abs().mean(), (res.y - res.pB).abs().mean()


def block_bootstrap_r2(res, block=BLOCK, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    T = len(res)
    starts = np.arange(0, T - block + 1)
    vals = []
    for _ in range(n):
        picks = rng.choice(starts, size=int(np.ceil(T / block)))
        idx = np.concatenate([np.arange(s, s + block) for s in picks])[:T]
        vals.append(oos_r2(res.iloc[idx]))
    return tuple(np.percentile(vals, [2.5, 97.5]))


def find_episodes(stress, threshold=EPISODE_THRESHOLD, gap=6):
    """Runs above threshold; runs separated by fewer than `gap` months below are merged."""
    above = stress > threshold
    raw, cur = [], None
    for t, a in above.items():
        if a:
            cur = [t, t] if cur is None else [cur[0], t]
        elif cur is not None:
            raw.append(cur)
            cur = None
    if cur is not None:
        raw.append(cur)
    merged = []
    for s, e in raw:
        if merged:
            months_between = (s.year - merged[-1][1].year) * 12 + (s.month - merged[-1][1].month) - 1
            if months_between < gap:
                merged[-1][1] = e
                continue
        merged.append([s, e])
    return [(s, e) for s, e in merged]


def leave_one_episode_out(res, episodes, h):
    rows = []
    for s, e in episodes:
        if not (res.index[0] <= s <= res.index[-1]):
            continue
        lo = s - pd.DateOffset(months=h)
        keep = res[(res.index < lo) | (res.index > e)]
        rows.append({"episode_start": s.strftime("%Y-%m"), "episode_end": e.strftime("%Y-%m"),
                     "months_dropped": len(res) - len(keep), "r2_without": round(float(oos_r2(keep)), 4)})
    return pd.DataFrame(rows)


def verdict(r2, ci, loeo, n_episodes):
    lo, hi = ci
    c1, c2 = r2 >= R2_MIN, lo > 0
    n_neg = int((loeo["r2_without"] <= 0).sum()) if len(loeo) else 99
    c3 = n_neg <= 1
    if n_episodes < 4:
        v = "INCONCLUSIVE (fewer than four stress episodes in the evaluation period)"
    elif c1 and c2 and c3:
        v = "SUPPORTED"
    elif lo <= 0 and hi >= R2_MIN:
        v = "INCONCLUSIVE (interval includes both 0 and 0.02)"
    elif c1 and c2 and not c3:
        v = "NOT SUPPORTED (not robust to dropping episodes)"
    else:
        v = "NOT SUPPORTED"
    return v, c1, c2, c3


def run_spec(df_feat, stress, name, kind, h):
    df = add_outcome(df_feat, kind, h)
    res = oos_forecasts(df, h)
    r2 = oos_r2(res)
    ci = block_bootstrap_r2(res)
    eps = find_episodes(stress)
    last_eval = res.index[-1]
    contributing = [(s, e) for s, e in eps if res.index[0] <= s <= last_eval]
    loeo = leave_one_episode_out(res, contributing, h)
    v, c1, c2, c3 = verdict(r2, ci, loeo, len(contributing))
    maeA, maeB = mae_pair(res)
    row = {"spec": name, "first_forecast": res.index[0].strftime("%Y-%m"), "last_outcome_month": last_eval.strftime("%Y-%m"),
           "oos_months": len(res), "episodes_in_eval": len(contributing),
           "mse_A": round(float(((res.y - res.pA) ** 2).mean()), 4), "mse_B": round(float(((res.y - res.pB) ** 2).mean()), 4),
           "oos_r2_B_vs_A": round(float(r2), 4), "ci95_lo": round(float(ci[0]), 4), "ci95_hi": round(float(ci[1]), 4),
           "mae_A": round(float(maeA), 4), "mae_B": round(float(maeB), 4),
           "cond1_r2_ge_0.02": c1, "cond2_ci_excludes_0": c2, "cond3_loeo_ok": c3,
           "episodes_negative_when_dropped": int((loeo["r2_without"] <= 0).sum()) if len(loeo) else None,
           "verdict": v}
    return row, res, loeo, eps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="pipeline test only; NOT a result")
    a = ap.parse_args()
    if a.synthetic:
        sent, stress = make_synthetic()
        tag = "synthetic"
    else:
        sent, stress = load_real("UMCSENT", "STLFSI4")
        tag = "real"
    feat = build_features(sent, stress)
    OUT.mkdir(exist_ok=True)
    rows, loeo_all, primary_res = [], [], None
    for name, kind, h, primary in SPECS:
        try:
            row, res, loeo, eps = run_spec(feat, stress, name, kind, h)
        except Exception as e:
            rows.append({"spec": name, "verdict": f"not estimable: {e}"})
            continue
        row["primary"] = primary
        rows.append(row)
        loeo = loeo.assign(spec=name)
        loeo_all.append(loeo)
        if primary:
            primary_res = res
    table = pd.DataFrame(rows)
    table.to_csv(OUT / f"phase1_results_{tag}.csv", index=False)
    if loeo_all:
        pd.concat(loeo_all).to_csv(OUT / f"phase1_leave_one_episode_out_{tag}.csv", index=False)
    pd.DataFrame([{"start": s.strftime("%Y-%m"), "end": e.strftime("%Y-%m")} for s, e in find_episodes(stress)]
                 ).to_csv(OUT / f"phase1_episodes_{tag}.csv", index=False)
    if primary_res is not None:
        primary_res.to_csv(OUT / f"phase1_primary_forecasts_{tag}.csv")
        _plot(primary_res, OUT / f"phase1_primary_{tag}.png")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(table.drop(columns=["mse_A", "mse_B"], errors="ignore").to_string(index=False))
    for l in loeo_all:
        print("\nLeave-one-episode-out:", l["spec"].iloc[0]); print(l.drop(columns="spec").to_string(index=False))


def _plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gain = ((res.y - res.pA) ** 2 - (res.y - res.pB) ** 2).cumsum()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gain.index, gain, lw=1.2)
    ax.axhline(0, color="k", lw=.6)
    ax.set_ylabel("Cumulative squared-error gain of B over A")
    ax.set_title("Severity(3): above zero = sentiment model B beating baseline A")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


if __name__ == "__main__":
    main()
