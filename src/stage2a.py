"""Phase 1, Stage 2a: does the excess bond premium (EBP) improve forecasts of the
severity and persistence of financial stress beyond a stress-index baseline?

Implements PREREGISTRATION_STAGE2A.md exactly (committed before this code was run).
Reuses the Stage 1 functions for outcomes, estimation windows, bootstrap, episodes,
leave-one-episode-out and the verdict. Only the indicator and its features differ.
Do not change settings here after results have been seen; add a dated note instead.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

import phase1 as p1
from phase1 import (add_outcome, oos_r2, mae_pair, block_bootstrap_r2, find_episodes,
                    leave_one_episode_out, verdict, _ols_predict, MIN_TRAIN, SPECS)
from clark_west import clark_west
from data import load_real, to_monthly, RAW_DIR, make_synthetic

OUT = Path(__file__).resolve().parents[1] / "outputs"
EBP_FILE = RAW_DIR / "ebp_csv.csv"
FEATS_A = ["stress", "stress_chg3"]
FEATS_B = FEATS_A + ["ebp", "ebp_chg3"]          # level and 3-month change, no standardization


def load_ebp(path=EBP_FILE):
    df = pd.read_csv(path)
    s = pd.Series(pd.to_numeric(df["ebp"], errors="coerce").values,
                  index=pd.to_datetime(df["date"]), name="ebp")
    return s.dropna().asfreq("MS")


def build_features(ebp, stress):
    """EBP features are built on the full continuous EBP history before merging."""
    f = pd.DataFrame({"ebp": ebp})
    f["ebp_chg3"] = ebp.diff(3)
    df = pd.concat([f, stress.rename("stress")], axis=1).dropna()
    df["stress_chg3"] = stress.diff(3).reindex(df.index)
    return df.dropna()


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
    t_cw, p_cw = clark_west(res, h)
    maeA, maeB = mae_pair(res)
    row = {"spec": name, "first_forecast": res.index[0].strftime("%Y-%m"),
           "last_outcome_month": last_eval.strftime("%Y-%m"),
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
    return row, res, loeo, eps


def run_all(feat, stress):
    rows, loeos, primary_res = [], [], None
    for name, kind, h, primary in SPECS:
        try:
            row, res, loeo, _ = run_spec(feat, stress, name, kind, h)
        except Exception as e:
            rows.append({"spec": name, "verdict": f"not estimable: {e}"})
            continue
        row["primary"] = primary
        rows.append(row)
        loeos.append(loeo.assign(spec=name))
        if primary:
            primary_res = res
    return pd.DataFrame(rows), loeos, primary_res


def _plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gain = ((res.y - res.pA) ** 2 - (res.y - res.pB) ** 2).cumsum()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gain.index, gain, lw=1.2)
    ax.axhline(0, color="k", lw=.6)
    ax.set_ylabel("Cumulative squared-error gain of B over A")
    ax.set_title("Severity(3): above zero = excess-bond-premium model B beating baseline A")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="pipeline test only; NOT a result")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.synthetic:
        ebp, stress = make_synthetic()
        tag = "synthetic"
    else:
        _, stress = load_real("UMCSENT", "STLFSI4")
        ebp = load_ebp()
        tag = "real"
    feat = build_features(ebp, stress)
    table, loeos, primary_res = run_all(feat, stress)
    table.to_csv(OUT / f"stage2a_results_{tag}.csv", index=False)
    if loeos:
        pd.concat(loeos).to_csv(OUT / f"stage2a_leave_one_episode_out_{tag}.csv", index=False)
    pd.DataFrame([{"start": s.strftime("%Y-%m"), "end": e.strftime("%Y-%m")} for s, e in find_episodes(stress)]
                 ).to_csv(OUT / f"stage2a_episodes_{tag}.csv", index=False)
    if primary_res is not None:
        primary_res.to_csv(OUT / f"stage2a_primary_forecasts_{tag}.csv")
        _plot(primary_res, OUT / f"stage2a_primary_{tag}.png")
    # Descriptive (registered, section 7): how much of the EBP is already in the stress index
    both = feat[["ebp", "stress"]]
    corr = pd.DataFrame([{"sample": f"{both.index[0]:%Y-%m} to {both.index[-1]:%Y-%m}", "n": len(both),
                          "corr_levels_ebp_stress": round(float(both.ebp.corr(both.stress)), 3),
                          "corr_3m_changes": round(float(feat.ebp_chg3.corr(feat.stress_chg3)), 3)}])
    corr.to_csv(OUT / f"stage2a_correlation_{tag}.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(table.drop(columns=["mse_A", "mse_B"], errors="ignore").to_string(index=False))
    for l in loeos:
        print("\nLeave-one-episode-out:", l["spec"].iloc[0]); print(l.drop(columns="spec").to_string(index=False))
    print("\nDescriptive correlation:"); print(corr.to_string(index=False))


if __name__ == "__main__":
    main()
