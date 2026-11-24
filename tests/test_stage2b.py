import hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import stage2b as s2


def _series(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1973-01-01", periods=n, freq="MS")
    u = pd.Series(5 + np.cumsum(rng.normal(0, .1, n)), index=idx)
    e = pd.Series(rng.normal(0, 1, n), index=idx)
    return u, e


def test_outcome_uses_only_the_future():
    u, e = _series()
    feat = s2.build_features(u, e)
    df = s2.add_outcome(feat, u, 12)
    t = df.index[50]
    assert df.loc[t, "y"] == pytest.approx(u.loc[t + pd.DateOffset(months=12)] - u.loc[t])


def test_missing_month_is_dropped_not_filled():
    u, e = _series()
    gap = u.index[200]
    u2 = u.copy(); u2.loc[gap] = np.nan
    df = s2.add_outcome(s2.build_features(u2, e), u2, 12)
    assert gap not in df.index                                   # its own row
    assert gap - pd.DateOffset(months=12) not in df.index        # outcome needs it
    assert gap + pd.DateOffset(months=3) not in df.index         # 3-month change needs it
    assert not df.isna().any().any()                             # nothing filled


def test_training_windows_close_before_forecast_year():
    u, e = _series()
    df = s2.add_outcome(s2.build_features(u, e), u, 12)
    res = s2.oos_forecasts(df, 12, 60)
    first = res.index[0]
    cutoff = pd.Timestamp(f"{first.year}-01-01") - pd.DateOffset(months=13)
    assert (df.index <= cutoff).sum() >= 60
    prev = pd.Timestamp(f"{first.year - 1}-01-01") - pd.DateOffset(months=13)
    assert (df.index <= prev).sum() < 60                         # earliest possible year


def test_features_use_only_past_and_current():
    u, e = _series()
    f1 = s2.build_features(u, e)
    u2 = u.copy(); u2.iloc[-1] += 100; e2 = e.copy(); e2.iloc[-1] += 100
    f2 = s2.build_features(u2, e2)
    pd.testing.assert_frame_equal(f1.iloc[:-1], f2.iloc[:-1])


def test_planted_signal_is_detected_end_to_end():
    rng = np.random.default_rng(3)
    n = 500
    idx = pd.date_range("1973-01-01", periods=n, freq="MS")
    e = pd.Series(np.cumsum(rng.normal(0, .3, n)) * .3 + rng.normal(0, .5, n), index=idx)
    u = pd.Series(np.nan, index=idx); u.iloc[0] = 5.0
    for i in range(1, n):
        u.iloc[i] = u.iloc[i - 1] + 0.5 * e.iloc[max(i - 12, 0)] * .1 + rng.normal(0, .05)
    feat = s2.build_features(u, e)
    eps = [(idx[i], idx[i + 5]) for i in range(150, 450, 60)]
    row, res, loeo = s2.run_spec(feat, u, eps, "DeltaU(12)", 12, 60, "test")
    assert row["oos_r2_B_vs_A"] > 0.02


def test_registered_files_match_their_checksums():
    raw = Path(__file__).resolve().parents[1] / "data" / "raw"
    expect = {"UNRATE.csv": "fb669461abc34e00324b940be6bad1c7f89117652f28587196a7b8bf4a9f56a1",
              "USRECM.csv": "23463db4e751eab4b9aa570b3070737a01cb0ebe119f29d751eb6cf940666850",
              "ebp_csv.csv": "caa16e0619cb5399b9c8f44433868351f01973f9594c50a4f1f87dd0856542c5"}
    for name, h in expect.items():
        p = raw / name
        if p.exists():
            assert hashlib.sha256(p.read_bytes()).hexdigest() == h


def test_real_data_shapes_and_episodes():
    raw = Path(__file__).resolve().parents[1] / "data" / "raw"
    if not (raw / "UNRATE.csv").exists():
        pytest.skip("real data not present")
    u = s2.load_unrate()
    assert len(u) == 946 and u.index[0] == pd.Timestamp("1948-01-01") and u.index[-1] == pd.Timestamp("2026-10-01")
    assert list(u[u.isna()].index) == [pd.Timestamp("2025-10-01")]
    eps = s2.load_recession_episodes()
    assert [(s.strftime("%Y-%m"), e.strftime("%Y-%m")) for s, e in eps] == [
        ("1973-11", "1975-03"), ("1980-01", "1980-07"), ("1981-07", "1982-11"),
        ("1990-07", "1991-03"), ("2001-03", "2001-11"), ("2007-12", "2009-06"), ("2020-02", "2020-04")]


def test_expected_first_forecasts_from_dates_alone():
    raw = Path(__file__).resolve().parents[1] / "data" / "raw"
    if not (raw / "UNRATE.csv").exists():
        pytest.skip("real data not present")
    u, e = s2.load_unrate(), s2.load_ebp()
    feat = s2.build_features(u, e)
    first = {}
    for h in (12, 6):
        df = s2.add_outcome(feat, u, h)
        for mt in (60, 84):
            first[(h, mt)] = s2.oos_forecasts(df, h, mt).index[0].year
    assert first == {(12, 60): 1980, (12, 84): 1982, (6, 60): 1979, (6, 84): 1981}


def test_synthetic_pipeline_runs():
    u, e, eps = s2._synthetic()
    table, loeos, sens, prim = s2.run_all(s2.build_features(u, e), u, eps)
    assert len(table) == 4 and prim is not None and len(sens) == 2
