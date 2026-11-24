import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import pandas as pd
from data import make_synthetic
from phase1 import add_outcome
from stage2a import build_features, oos_forecasts, run_spec, load_ebp


def test_outcomes_use_only_future_months():
    ind, stress = make_synthetic()
    df = add_outcome(build_features(ind, stress), "severity", 3)
    t = df.index[20]
    assert np.isclose(df.loc[t, "y"], stress.loc[t:].iloc[1:4].max())


def test_training_windows_closed_before_forecast_year():
    ind, stress = make_synthetic()
    h = 6
    df = add_outcome(build_features(ind, stress), "severity", h)
    res1 = oos_forecasts(df, h)
    df2 = df.copy()
    df2.loc[df2.index >= "2005-01-01", "y"] += 100.0
    res2 = oos_forecasts(df2, h)
    first = res1[res1.index.year == 2005].index
    assert np.allclose(res1.loc[first, ["pA", "pB"]], res2.loc[first, ["pA", "pB"]])


def test_features_use_only_past_and_current():
    ind, stress = make_synthetic()
    f1 = build_features(ind, stress)
    ind2 = ind.copy(); ind2.iloc[-5:] += 50.0     # change only the last months
    f2 = build_features(ind2, stress)
    t = f1.index[-20]
    assert np.allclose(f1.loc[t, ["ebp", "ebp_chg3"]], f2.loc[t, ["ebp", "ebp_chg3"]])


def test_planted_signal_detected_end_to_end():
    ind, stress = make_synthetic()
    feat = build_features(ind, stress)
    row, res, loeo, eps = run_spec(feat, stress, "Severity(3)", "severity", 3)
    assert row["oos_r2_B_vs_A"] > 0.02 and row["oos_months"] > 100
    assert 0 <= row["clark_west_p_one_sided"] <= 1


def test_real_ebp_file_shape():
    p = Path(__file__).resolve().parents[1] / "data" / "raw" / "ebp_csv.csv"
    if not p.exists():
        return                                   # raw data are not stored in the repository
    s = load_ebp(p)
    assert s.index[0] == pd.Timestamp("1973-01-01") and len(s) == 646 and s.notna().all()
