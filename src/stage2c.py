"""Phase 1, Stage 2c: does bank loan growth (Federal Reserve H.8, series B1020NCBCMG, break adjusted)
improve out-of-sample forecasts of the 12-month change in the U.S. unemployment rate beyond an
unemployment-only baseline?

Implements PREREGISTRATION_STAGE2C.md exactly (committed as b5a5454 before this code was written).
Same design as Stage 2b; reuses its loaders, forecasting loop and episode definition. Only the
indicator differs, and the sample is cut to start at April 1973 to match Stage 2b.
Do not change settings here after results have been seen; add a dated note instead.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from phase1 import (oos_r2, mae_pair, block_bootstrap_r2, leave_one_episode_out, verdict, _ols_predict)
from clark_west import clark_west
from stage2a import load_ebp
from stage2b import (load_unrate, load_recession_episodes, add_outcome,
                     MIN_TRAIN_PRIMARY, MIN_TRAIN_SENSITIVITY, SPECS, COVID_START, COVID_END)
from data import RAW_DIR

OUT = Path(__file__).resolve().parents[1] / "outputs"

# ---- registered settings (windows, specs and COVID window imported unchanged from Stage 2b) ----
FEATS_A = ["u", "u_chg3"]
FEATS_B = FEATS_A + ["g", "g_chg3"]               # level and 3-month change, no smoothing, no standardization


H8_FILE = RAW_DIR / "H8_B1020NCBCMG_monthly.csv"
FIRST_ROW = pd.Timestamp("1973-04-01")   # registered: rows before April 1973 are not used (matches Stage 2b)


def load_loan_growth(path=H8_FILE):
    """Monthly annualized, break-adjusted growth of loans and leases in bank credit, as published."""
    df = pd.read_csv(path)
    s = pd.Series(pd.to_numeric(df["loans_growth"], errors="coerce").values,
                  index=pd.PeriodIndex(df["month"], freq="M").to_timestamp(), name="g")
    return s.asfreq("MS")


def build_features(u, g):
    """3-month changes are built on each full continuous series before merging; rows before
    April 1973 are then dropped (registered). Rows with any missing feature are dropped later, not filled."""
    f = pd.DataFrame({"g": g})
    f["g_chg3"] = g.diff(3)
    f["u"] = u.reindex(f.index)
    f["u_chg3"] = u.diff(3).reindex(f.index)
    return f[f.index >= FIRST_ROW]


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
    ax.set_title("DeltaU(12): above zero = loan-growth model B beating unemployment-only baseline A")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="pipeline test only; NOT a result")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.synthetic:
        u, g, episodes = _synthetic()
        tag = "synthetic"
    else:
        u, g, episodes = load_unrate(), load_loan_growth(), load_recession_episodes()
        tag = "real"
    feat = build_features(u, g)
    table, loeos, sens, primary_res = run_all(feat, u, episodes)
    table.to_csv(OUT / f"stage2c_results_{tag}.csv", index=False)
    sens.to_csv(OUT / f"stage2c_sensitivity_{tag}.csv", index=False)
    if loeos:
        pd.concat(loeos).to_csv(OUT / f"stage2c_leave_one_episode_out_{tag}.csv", index=False)
    pd.DataFrame([{"start": s.strftime("%Y-%m"), "end": e.strftime("%Y-%m")} for s, e in episodes]
                 ).to_csv(OUT / f"stage2c_episodes_{tag}.csv", index=False)
    if primary_res is not None:
        primary_res.to_csv(OUT / f"stage2c_primary_forecasts_{tag}.csv")
        _plot(primary_res, OUT / f"stage2c_primary_{tag}.png")
    def _corr(a, b, label):
        both = pd.concat([a, b], axis=1).dropna()
        chg = pd.concat([a.diff(3), b.diff(3)], axis=1).dropna()
        return {"pair": label, "sample": f"{both.index[0]:%Y-%m} to {both.index[-1]:%Y-%m}", "n": len(both),
                "corr_levels": round(float(both.corr().iloc[0, 1]), 3),
                "corr_3m_changes": round(float(chg.corr().iloc[0, 1]), 3)}
    rows = [_corr(g[g.index >= FIRST_ROW], u, "loan growth vs unemployment rate")]
    if not a.synthetic:
        e = load_ebp()
        rows.append(_corr(g[g.index.isin(e.index)], e, "loan growth vs excess bond premium"))
    corr = pd.DataFrame(rows)
    corr.to_csv(OUT / f"stage2c_correlation_{tag}.csv", index=False)
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
    g = pd.Series(np.cumsum(rng.normal(0, .15, n)) * .2 + rng.normal(0, .1, n), index=idx)
    u = pd.Series(5 + np.cumsum(rng.normal(0, .08, n)), index=idx)
    if signal:
        u = u + (g.shift(6).fillna(0) * 1.0).cumsum() * .02
    eps = [(idx[i], idx[i + 6]) for i in range(100, n - 40, 90)]
    return u, g, eps


if __name__ == "__main__":
    main()
