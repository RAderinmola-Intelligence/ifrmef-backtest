import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from data import make_synthetic
from backtest import build_frame, run


def test_no_lookahead_features():
    sent, stress = make_synthetic()
    df = build_frame(sent, stress, horizon=3, threshold=0.5)
    # target must depend only on FUTURE stress; features only on past/current
    t = df.index[10]
    fut = stress.loc[t:].iloc[1:4].max() > 0.5
    assert bool(df.loc[t, "y"]) == bool(fut)
    assert (df.stress <= 0.5).all()  # onset-only sample


def test_runs_end_to_end_and_planted_signal_detected():
    sent, stress = make_synthetic()
    summary, res = run(sent, stress, horizon=3, threshold=0.5, label="synthetic")
    assert summary["oos_months"] > 50
    assert 0 <= summary["auc_A_baseline"] <= 1
    assert summary["auc_B_with_sentiment"] > summary["auc_A_baseline"] + 0.03


def test_grid_reports_every_setting():
    from backtest import run_grid
    sent, stress = make_synthetic()
    g = run_grid(sent, stress, [3, 6], [0.3, 0.5], "synthetic")
    assert len(g) == 4
