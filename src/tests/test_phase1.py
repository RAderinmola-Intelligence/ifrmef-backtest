import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import pandas as pd
from data import make_synthetic
from phase1 import (build_features, add_outcome, oos_forecasts, oos_r2, find_episodes,
                    verdict, run_spec, leave_one_episode_out)


def test_outcomes_use_only_future_months():
    sent, stress = make_synthetic()
    df = add_outcome(build_features(sent, stress), "severity", 3)
    t = df.index[20]
    assert np.isclose(df.loc[t, "y"], stress.loc[t:].iloc[1:4].max())
    dp = add_outcome(build_features(sent, stress), "persistence", 6)
    assert np.isclose(dp.loc[t, "y"], (stress.loc[t:].iloc[1:7] > 0.5).sum())


def test_training_windows_closed_before_forecast_year():
    sent, stress = make_synthetic()
    h = 6
    df = add_outcome(build_features(sent, stress), "severity", h)
    # corrupt the future: change stress after a forecast year starts; forecasts for that year must not move
    res1 = oos_forecasts(df, h)
    yr = 2005
    df2 = df.copy()
    df2.loc[df2.index >= f"{yr}-01-01", "y"] += 100.0   # outcomes that only close after Jan of yr
    res2 = oos_forecasts(df2, h)
    first = res1[res1.index.year == yr].index
    assert np.allclose(res1.loc[first, ["pA", "pB"]], res2.loc[first, ["pA", "pB"]])


def test_episode_merging_and_gap():
    idx = pd.date_range("2000-01-01", periods=40, freq="MS")
    s = pd.Series(0.0, idx)
    s.iloc[2:4] = 1          # run 1
    s.iloc[7:9] = 1          # 3 months below -> merges with run 1
    s.iloc[20:22] = 1        # 11 months below -> separate
    eps = find_episodes(s)
    assert len(eps) == 2 and eps[0] == (idx[2], idx[8]) and eps[1][0] == idx[20]


def test_verdict_rules():
    loeo_ok = pd.DataFrame({"r2_without": [0.03, 0.02, 0.04, 0.05]})
    assert verdict(0.05, (0.01, 0.09), loeo_ok, 5)[0] == "SUPPORTED"
    assert verdict(0.05, (0.01, 0.09), loeo_ok, 3)[0].startswith("INCONCLUSIVE")
    assert verdict(-0.05, (-0.2, 0.1), loeo_ok, 5)[0].startswith("INCONCLUSIVE")
    assert verdict(-0.05, (-0.2, 0.01), loeo_ok, 5)[0] == "NOT SUPPORTED"
    bad = pd.DataFrame({"r2_without": [-0.01, -0.02, 0.04, 0.05]})
    assert verdict(0.05, (0.01, 0.09), bad, 5)[0].startswith("NOT SUPPORTED")


def test_planted_signal_detected_end_to_end():
    sent, stress = make_synthetic()
    feat = build_features(sent, stress)
    row, res, loeo, eps = run_spec(feat, stress, "Severity(3)", "severity", 3)
    assert row["oos_r2_B_vs_A"] > 0.02
    assert row["oos_months"] > 100
