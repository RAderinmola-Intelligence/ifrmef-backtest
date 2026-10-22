"""Does consumer sentiment add out-of-sample information for warning of
financial-stress onset, beyond what the stress index itself already shows?

Design (no look-ahead):
  * Unit: month t. Only months NOT already in stress are used (onset warning).
  * Target: stress index exceeds THRESHOLD in any of months t+1..t+H.
  * Model A (baseline): current stress level and its 3-month change.
  * Model B: Model A plus sentiment z-score (rolling window) and 3-month change.
  * Expanding-window, out-of-sample: models are re-fit each year using only
    data whose outcome window had fully closed before the forecast month.
  * Metric: out-of-sample AUC, A vs B, with a block-bootstrap interval for B - A.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data import load_real, make_synthetic

OUT = Path(__file__).resolve().parents[1] / "outputs"


def build_frame(sent, stress, horizon, threshold, z_window=120):
    # Sentiment features are built on the full continuous monthly sentiment history
    # (UMCSENT is monthly and gap-free from 1978) BEFORE merging with the shorter stress
    # series, so the rolling window does not consume the start of the stress sample.
    sent = sent[sent.index >= "1978-01-01"].asfreq("MS")
    sfeat = pd.DataFrame({"sent": sent})
    sfeat["sent_z"] = (sent - sent.rolling(z_window).mean()) / sent.rolling(z_window).std()
    sfeat["sent_chg3"] = sent.diff(3)
    df = pd.concat([sfeat, stress.rename("stress")], axis=1).dropna()
    df["stress_chg3"] = stress.diff(3).reindex(df.index)
    fut = pd.concat([df.stress.shift(-k) for k in range(1, horizon + 1)], axis=1)
    df["y"] = (fut.max(axis=1) > threshold).astype(float).where(fut.notna().all(axis=1))
    df = df[df.stress <= threshold]  # onset only: exclude months already in stress
    return df.dropna()


FEATS_A = ["stress", "stress_chg3"]
FEATS_B = FEATS_A + ["sent_z", "sent_chg3"]


def _fit(train, feats):
    m = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))
    m.fit(train[feats], train["y"])
    return m


def oos_predictions(df, horizon, min_train=120):
    """Expanding window. Training rows must have outcome windows closed before the forecast month."""
    preds = {"A": [], "B": []}
    idx, years = [], sorted(set(df.index.year))
    for yr in years:
        test = df[df.index.year == yr]
        cutoff = pd.Timestamp(f"{yr}-01-01") - pd.DateOffset(months=horizon)
        train = df[df.index <= cutoff]
        if len(train) < min_train or train.y.nunique() < 2 or test.empty:
            continue
        for name, feats in (("A", FEATS_A), ("B", FEATS_B)):
            preds[name].append(pd.Series(_fit(train, feats).predict_proba(test[feats])[:, 1], index=test.index))
        idx.append(test.index)
    if not idx:
        raise RuntimeError("Not enough history to produce out-of-sample forecasts.")
    pa, pb = pd.concat(preds["A"]), pd.concat(preds["B"])
    return pd.DataFrame({"y": df.loc[pa.index, "y"], "pA": pa, "pB": pb})


def block_bootstrap_auc_diff(res, block=12, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    T, diffs = len(res), []
    starts = np.arange(0, T - block + 1)
    for _ in range(n):
        picks = rng.choice(starts, size=int(np.ceil(T / block)))
        samp = res.iloc[np.concatenate([np.arange(s, s + block) for s in picks])[:T]]
        if samp.y.nunique() < 2:
            continue
        diffs.append(roc_auc_score(samp.y, samp.pB) - roc_auc_score(samp.y, samp.pA))
    return np.percentile(diffs, [2.5, 97.5])


def run(sent, stress, horizon=3, threshold=1.0, label="real"):
    df = build_frame(sent, stress, horizon, threshold)
    res = oos_predictions(df, horizon)
    summary = {
        "data": label, "horizon_months": horizon, "threshold": threshold,
        "oos_months": len(res), "onset_events": int(res.y.sum()),
        "base_rate": round(float(res.y.mean()), 3),
        "auc_A_baseline": round(roc_auc_score(res.y, res.pA), 3),
        "auc_B_with_sentiment": round(roc_auc_score(res.y, res.pB), 3),
        "brier_A": round(brier_score_loss(res.y, res.pA), 3),
        "brier_B": round(brier_score_loss(res.y, res.pB), 3),
    }
    summary["auc_diff_B_minus_A"] = round(summary["auc_B_with_sentiment"] - summary["auc_A_baseline"], 3)
    lo, hi = block_bootstrap_auc_diff(res)
    summary["auc_diff_95ci"] = (round(float(lo), 3), round(float(hi), 3))
    return summary, res


def plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(res.index, res.pA, label="A: stress only", lw=1, alpha=.8)
    ax.plot(res.index, res.pB, label="B: stress + sentiment", lw=1, alpha=.8)
    ax.scatter(res.index[res.y == 1], [1.02] * int((res.y == 1).sum()), marker="|", c="k", label="Onset followed (actual)")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Out-of-sample warning probability")
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def run_grid(sent, stress, horizons, thresholds, label):
    """Run every horizon x threshold combination and report ALL of them.
    Fix the grid before looking at results, so no single setting is cherry-picked."""
    rows = []
    for h in horizons:
        for th in thresholds:
            try:
                summ, _ = run(sent, stress, h, th, label)
                rows.append(summ)
            except Exception as e:  # too few events or history for this setting
                rows.append({"data": label, "horizon_months": h, "threshold": th, "note": f"not estimable: {e}"})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentiment", default="UMCSENT")
    ap.add_argument("--stress", default="STLFSI4")
    ap.add_argument("--horizon", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=1.0)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--grid", action="store_true", help="run all horizon x threshold combinations")
    ap.add_argument("--horizons", default="3,6,12")
    ap.add_argument("--thresholds", default="0.5,1.0,1.5")
    ap.add_argument("--synthetic", action="store_true", help="pipeline test only; NOT a result")
    a = ap.parse_args()
    if a.synthetic:
        sent, stress = make_synthetic()
        label = "SYNTHETIC (pipeline test only, not a finding)"
    else:
        sent, stress = load_real(a.sentiment, a.stress, a.refresh)
        label = f"{a.sentiment} vs {a.stress}"
    OUT.mkdir(exist_ok=True)
    if a.grid:
        hs = [int(x) for x in a.horizons.split(",")]
        ths = [float(x) for x in a.thresholds.split(",")]
        g = run_grid(sent, stress, hs, ths, label)
        tag = "synthetic" if a.synthetic else "real"
        g.to_csv(OUT / f"grid_{tag}.csv", index=False)
        cols = [c for c in ["horizon_months", "threshold", "oos_months", "onset_events", "base_rate",
                            "auc_A_baseline", "auc_B_with_sentiment", "auc_diff_B_minus_A", "auc_diff_95ci", "note"] if c in g.columns]
        print(g[cols].to_string(index=False))
        return
    summary, res = run(sent, stress, a.horizon, a.threshold, label)
    tag = "synthetic" if a.synthetic else "real"
    res.to_csv(OUT / f"oos_predictions_{tag}.csv")
    plot(res, OUT / f"oos_probabilities_{tag}.png")
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
