"""Phase 1, Stage 2b: does the excess bond premium (EBP) improve out-of-sample forecasts of the
12-month change in the U.S. unemployment rate beyond an unemployment-only baseline?

Implements PREREGISTRATION_STAGE2B.md exactly (committed as 19e3181 before this code was written).
Reuses the earlier stages' functions for estimation windows' bootstrap, leave-one-episode-out,
the verdict and Clark-West. Only the outcome, baseline and episode definition differ.
Do not change settings here after results have been seen; add a dated note instead.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from phase1 import (oos_r2, mae_pair, block_bootstrap_r2, leave_one_episode_out, verdict, _ols_predict)
from clark_west import clark_west
from stage2a import load_ebp
from data import RAW_DIR

OUT = Path(__file__).resolve().parents[1] / "outputs"
UNRATE_FILE = RAW_DIR / "UNRATE.csv"
USRECM_FILE = RAW_DIR / "USRECM.csv"

# ---- registered settings ---------------------------------------------------------
MIN_TRAIN_PRIMARY = 60
MIN_TRAIN_SENSITIVITY = 84
FEATS_A = ["u", "u_chg3"]
FEATS_B = FEATS_A + ["ebp", "ebp_chg3"]            # level and 3-month change, no standardization
SPECS = [("DeltaU(12)", 12, True), ("DeltaU(6)", 6, False)]   # (name, horizon, primary)
COVID_START, COVID_END = pd.Timestamp("2020-01-01"), pd.Timestamp("2021-12-01")
FIRST_EPISODE_YEAR = 1973


def load_unrate(path=UNRATE_FILE):
    """Monthly UNRATE. Blank values stay missing: they are never filled or interpolated."""
    df = pd.read_csv(path)
    s = pd.Series(pd.to_numeric(df["UNRATE"], errors="coerce").values,
                  index=pd.to_datetime(df["observation_date"]), name="u")
    return s.asfreq("MS")


def load_recession_episodes(path=USRECM_FILE):
    """Each run of USRECM == 1 since 1973 is one episode, as published, not merged."""
    df = pd.read_csv(path)
    r = pd.Series(pd.to_numeric(df["USRECM"], errors="coerce").values,
                  index=pd.to_datetime(df["observation_date"])).asfreq("MS")
    r = r[r.index.year >= FIRST_EPISODE_YEAR]
    eps, start, prev = [], None, None
    for t, v in r.items():
        if v == 1 and start is None:
            start = t
        if v != 1 and start is not None:
            eps.append((start, prev)); start = None
        prev = t
    if start is not None:
        eps.append((start, prev))
    return eps


def build_features(u, ebp):
    """3-month changes are built on each full continuous series before merging.
    Rows with any missing feature are dropped later, not filled."""
    f = pd.DataFrame({"ebp": ebp})
    f["ebp_chg3"] = ebp.diff(3)
    f["u"] = u.reindex(f.index)
    f["u_chg3"] = u.diff(3).reindex(f.index)
    return f


def add_outcome(df, u, h):
    """DeltaU(h) = u[t+h] - u[t]. Rows missing any feature or the outcome are dropped."""
    out = df.copy()
    out["y"] = (u.shift(-h) - u).reindex(out.index)
    return out.dropna()


def oos_forecasts(df, h, min_train):
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


def _stats(res, h):
    r2 = oos_r2(res)
    ci = block_bootstrap_r2(res)
    t_cw, p_cw = clark_west(res, h)
    maeA, maeB = mae_pair(res)
    return r2, ci, t_cw, p_cw, maeA, maeB


def run_spec(feat, u, episodes, name, h, min_train, label):
    df = add_outcome(feat, u, h)
    res = oos_forecasts(df, h, min_train)
    r2, ci, t_cw, p_cw, maeA, maeB = _stats(res, h)
    contributing = [(s, e) for s, e in episodes if res.index[0] <= s <= res.index[-1]]
    loeo = leave_one_episode_out(res, contributing, h)
    v, c1, c2, c3 = verdict(r2, ci, loeo, len(contributing))
    row = {"spec": name, "setting": label, "min_train": min_train,
           "first_forecast": res.index[0].strftime("%Y-%m"), "last_outcome_month": res.index[-1].strftime("%Y-%m"),
           "oos_months": len(res), "episodes_in_eval": len(contributing),
           "mse_A": round(float(((res.y - res.pA) ** 2).mean()), 4),
           "mse_B": round(float(((res.y - res.pB) ** 2).mean()), 4),
           "oos_r2_B_vs_A": round(float(r2), 4),
           "ci95_lo": round(float(ci[0]), 4), "ci95_hi": round(float(ci[1]), 4),
           "mae_A": round(float(maeA), 4), "mae_B": round(float(maeB), 4),
           "clark_west_t": round(t_cw, 3), "clark_west_p_one_sided": round(p_cw, 4),
           "cond1_r2_ge_0.02": c1, "cond2_ci_excludes_0": c2, "cond3_loeo_ok": c3,
           "episodes_negative_when_dropped": int((loeo["r2_without"] <= 0).sum()) if len(loeo) else None,
           "verdict": v}
    return row, res, loeo


def run_excluding_covid(feat, u, name, h, min_train):
    """Registered sensitivity: drop evaluation months Jan 2020 to Dec 2021, recompute R2, interval, Clark-West."""
    df = add_outcome(feat, u, h)
    res = oos_forecasts(df, h, min_train)
    res = res[(res.index < COVID_START) | (res.index > COVID_END)]
    r2, ci, t_cw, p_cw, maeA, maeB = _stats(res, h)
    return {"spec": name, "setting": "excluding Jan 2020 to Dec 2021", "min_train": min_train,
            "oos_months": len(res), "oos_r2_B_vs_A": round(float(r2), 4),
            "ci95_lo": round(float(ci[0]), 4), "ci95_hi": round(float(ci[1]), 4),
            "mae_A": round(float(maeA), 4), "mae_B": round(float(maeB), 4),
            "clark_west_t": round(t_cw, 3), "clark_west_p_one_sided": round(p_cw, 4)}


def run_all(feat, u, episodes):
    rows, loeos, sens, primary_res = [], [], [], None
    for name, h, primary in SPECS:
        for mt, label in ((MIN_TRAIN_PRIMARY, "primary window (60)"), (MIN_TRAIN_SENSITIVITY, "sensitivity window (84)")):
            try:
                row, res, loeo = run_spec(feat, u, episodes, name, h, mt, label)
            except Exception as e:
                rows.append({"spec": name, "setting": label, "verdict": f"not estimable: {e}"})
                continue
            row["primary"] = bool(primary and mt == MIN_TRAIN_PRIMARY)
            rows.append(row)
            loeos.append(loeo.assign(spec=name, setting=label))
            if row["primary"]:
                primary_res = res
        sens.append(run_excluding_covid(feat, u, name, h, MIN_TRAIN_PRIMARY))
    return pd.DataFrame(rows), loeos, pd.DataFrame(sens), primary_res


def _plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gain = ((res.y - res.pA) ** 2 - (res.y - res.pB) ** 2).cumsum()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gain.index, gain, lw=1.2)
    ax.axhline(0, color="k", lw=.6)
    ax.set_ylabel("Cumulative squared-error gain of B over A")
    ax.set_title("DeltaU(12): above zero = excess-bond-premium model B beating unemployment-only baseline A")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="pipeline test only; NOT a result")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.synthetic:
        u, ebp, episodes = _synthetic()
        tag = "synthetic"
    else:
        u, ebp, episodes = load_unrate(), load_ebp(), load_recession_episodes()
        tag = "real"
    feat = build_features(u, ebp)
    table, loeos, sens, primary_res = run_all(feat, u, episodes)
    table.to_csv(OUT / f"stage2b_results_{tag}.csv", index=False)
    sens.to_csv(OUT / f"stage2b_sensitivity_{tag}.csv", index=False)
    if loeos:
        pd.concat(loeos).to_csv(OUT / f"stage2b_leave_one_episode_out_{tag}.csv", index=False)
    pd.DataFrame([{"start": s.strftime("%Y-%m"), "end": e.strftime("%Y-%m")} for s, e in episodes]
                 ).to_csv(OUT / f"stage2b_episodes_{tag}.csv", index=False)
    if primary_res is not None:
        primary_res.to_csv(OUT / f"stage2b_primary_forecasts_{tag}.csv")
        _plot(primary_res, OUT / f"stage2b_primary_{tag}.png")
    both = pd.concat([ebp, u], axis=1).dropna()
    chg = pd.concat([ebp.diff(3), u.diff(3)], axis=1).dropna()
    corr = pd.DataFrame([{"sample": f"{both.index[0]:%Y-%m} to {both.index[-1]:%Y-%m}", "n": len(both),
                          "corr_levels": round(float(both.corr().iloc[0, 1]), 3),
                          "corr_3m_changes": round(float(chg.corr().iloc[0, 1]), 3)}])
    corr.to_csv(OUT / f"stage2b_correlation_{tag}.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(table.drop(columns=["mse_A", "mse_B"], errors="ignore").to_string(index=False))
    print("\nSensitivity (excluding COVID months):"); print(sens.to_string(index=False))
    for l in loeos:
        print("\nLeave-one-episode-out:", l["spec"].iloc[0], l["setting"].iloc[0])
        print(l.drop(columns=["spec", "setting"]).to_string(index=False))
    print("\nCorrelation:"); print(corr.to_string(index=False))


def _synthetic(seed=1, n=600, signal=True):
    """Planted-signal data for pipeline tests only. Not a result."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1973-01-01", periods=n, freq="MS")
    ebp = pd.Series(np.cumsum(rng.normal(0, .15, n)) * .2 + rng.normal(0, .1, n), index=idx)
    u = pd.Series(5 + np.cumsum(rng.normal(0, .08, n)), index=idx)
    if signal:
        u = u + (ebp.shift(6).fillna(0) * 1.0).cumsum() * .02
    eps = [(idx[i], idx[i + 6]) for i in range(100, n - 40, 90)]
    return u, ebp, eps


if __name__ == "__main__":
    main()
