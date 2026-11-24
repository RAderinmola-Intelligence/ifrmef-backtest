import hashlib, re, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import stage2c as s3

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def _series(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1973-01-01", periods=n, freq="MS")
    u = pd.Series(5 + np.cumsum(rng.normal(0, .1, n)), index=idx)
    g = pd.Series(rng.normal(6, 3, n), index=idx)
    return u, g


def test_features_use_only_past_and_current():
    u, g = _series()
    f1 = s3.build_features(u, g)
    u2 = u.copy(); u2.iloc[-1] += 100; g2 = g.copy(); g2.iloc[-1] += 100
    f2 = s3.build_features(u2, g2)
    pd.testing.assert_frame_equal(f1.iloc[:-1], f2.iloc[:-1])


def test_sample_starts_april_1973_even_if_indicator_starts_earlier():
    idx = pd.date_range("1947-02-01", "2000-12-01", freq="MS")
    rng = np.random.default_rng(1)
    g = pd.Series(rng.normal(6, 3, len(idx)), index=idx)
    u = pd.Series(5 + rng.normal(0, .1, len(idx)).cumsum() * .1, index=idx)
    f = s3.build_features(u, g)
    assert f.index[0] == pd.Timestamp("1973-04-01")
    assert not f.isna().any().any()
    # the 3-month change in April 1973 uses January 1973 (not dropped data)
    assert f.loc["1973-04-01", "g_chg3"] == pytest.approx(g.loc["1973-04-01"] - g.loc["1973-01-01"])


def test_model_b_adds_exactly_the_registered_columns():
    assert s3.FEATS_A == ["u", "u_chg3"]
    assert s3.FEATS_B == ["u", "u_chg3", "g", "g_chg3"]


def test_missing_month_is_dropped_not_filled():
    u, g = _series()
    gap = u.index[200]
    u2 = u.copy(); u2.loc[gap] = np.nan
    df = s3.add_outcome(s3.build_features(u2, g), u2, 12)
    assert gap not in df.index and gap - pd.DateOffset(months=12) not in df.index
    assert gap + pd.DateOffset(months=3) not in df.index
    assert not df.isna().any().any()


def test_training_windows_close_before_forecast_year():
    u, g = _series()
    df = s3.add_outcome(s3.build_features(u, g), u, 12)
    res = s3.oos_forecasts(df, 12, 60)
    first = res.index[0]
    cutoff = pd.Timestamp(f"{first.year}-01-01") - pd.DateOffset(months=13)
    assert (df.index <= cutoff).sum() >= 60
    prev = pd.Timestamp(f"{first.year - 1}-01-01") - pd.DateOffset(months=13)
    assert (df.index <= prev).sum() < 60


def test_planted_signal_is_detected_end_to_end():
    rng = np.random.default_rng(3)
    n = 500
    idx = pd.date_range("1973-01-01", periods=n, freq="MS")
    g = pd.Series(np.cumsum(rng.normal(0, .3, n)) * .3 + rng.normal(0, .5, n), index=idx)
    u = pd.Series(np.nan, index=idx); u.iloc[0] = 5.0
    for i in range(1, n):
        u.iloc[i] = u.iloc[i - 1] + 0.5 * g.iloc[max(i - 12, 0)] * .1 + rng.normal(0, .05)
    feat = s3.build_features(u, g)
    eps = [(idx[i], idx[i + 5]) for i in range(150, 450, 60)]
    row, res, loeo = s3.run_spec(feat, u, eps, "DeltaU(12)", 12, 60, "test")
    assert row["oos_r2_B_vs_A"] > 0.02


def test_registered_files_match_their_checksums():
    expect = {"UNRATE.csv": "fb669461abc34e00324b940be6bad1c7f89117652f28587196a7b8bf4a9f56a1",
              "USRECM.csv": "23463db4e751eab4b9aa570b3070737a01cb0ebe119f29d751eb6cf940666850",
              "FRB_h8_xml.zip": "839aaa7fbbe7317ed5d34e84a29d6757ba0e3a3c5322ed46b32bcbe39d3ff59f",
              "H8_B1020NCBCMG_monthly.csv": "65c9a718fa1eb9af95b63e74da4b32747d2f1d680d247a3c74197e4dfcf813ac"}
    for name, h in expect.items():
        p = RAW / name
        if p.exists():
            assert hashlib.sha256(p.read_bytes()).hexdigest() == h, name


def test_extracted_series_equals_the_series_in_the_downloaded_zip():
    z = RAW / "FRB_h8_xml.zip"
    if not z.exists():
        pytest.skip("zip not present")
    with zipfile.ZipFile(z) as zf:
        s = zf.read("H8_data.xml").decode("utf-8")
    i = s.index('SERIES_NAME="B1020NCBCMG"'); j = s.index("</kf:Series>", i)
    obs = re.findall(r'OBS_VALUE="([^"]*)"[^>]*?TIME_PERIOD="([^"]+)"', s[i:j])
    xml = pd.Series({pd.Timestamp(t).to_period("M").to_timestamp(): float(v) for v, t in obs if v != ""})
    csv = s3.load_loan_growth().dropna().rename_axis(None)
    pd.testing.assert_series_equal(csv, xml.rename("g").asfreq("MS"), check_freq=False, check_names=False)


def test_real_data_shapes():
    if not (RAW / "H8_B1020NCBCMG_monthly.csv").exists():
        pytest.skip("real data not present")
    g = s3.load_loan_growth()
    assert g.index[0] == pd.Timestamp("1947-02-01") and g.index[-1] == pd.Timestamp("2026-10-01")
    assert g.isna().sum() == 0
    assert len(g[g.index >= "1973-01-01"]) == 646
    u = s3.load_unrate()
    assert list(u[u.isna()].index) == [pd.Timestamp("2025-10-01")]
    eps = s3.load_recession_episodes()
    assert [(a.strftime("%Y-%m"), b.strftime("%Y-%m")) for a, b in eps] == [
        ("1973-11", "1975-03"), ("1980-01", "1980-07"), ("1981-07", "1982-11"),
        ("1990-07", "1991-03"), ("2001-03", "2001-11"), ("2007-12", "2009-06"), ("2020-02", "2020-04")]


def test_expected_first_forecasts_from_dates_alone():
    if not (RAW / "H8_B1020NCBCMG_monthly.csv").exists():
        pytest.skip("real data not present")
    u, g = s3.load_unrate(), s3.load_loan_growth()
    feat = s3.build_features(u, g)
    first = {}
    for h in (12, 6):
        df = s3.add_outcome(feat, u, h)
        for mt in (60, 84):
            first[(h, mt)] = s3.oos_forecasts(df, h, mt).index[0].year
    assert first == {(12, 60): 1980, (12, 84): 1982, (6, 60): 1979, (6, 84): 1981}


def test_synthetic_pipeline_runs():
    u, g, eps = s3._synthetic()
    table, loeos, sens, prim = s3.run_all(s3.build_features(u, g), u, eps)
    assert len(table) == 4 and prim is not None and len(sens) == 2
