"""Data loading for the back-test.

Real data come from FRED public CSV downloads. A synthetic generator is
provided ONLY to test that the pipeline runs. Its output must never be
reported as a finding.
"""
from pathlib import Path
import numpy as np
import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def fetch_fred(series_id: str, refresh: bool = False) -> pd.Series:
    """Download a FRED series as a float Series indexed by date. Cached to data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{series_id}.csv"
    if refresh or not path.exists():
        df = pd.read_csv(FRED_URL.format(sid=series_id))
        df.to_csv(path, index=False)
    df = pd.read_csv(path)
    date_col, val_col = df.columns[0], df.columns[1]  # FRED has used DATE and observation_date
    s = pd.Series(pd.to_numeric(df[val_col], errors="coerce").values,
                  index=pd.to_datetime(df[date_col]), name=series_id)
    return s.dropna()


def to_monthly(s: pd.Series) -> pd.Series:
    """Monthly mean, indexed at month start."""
    return s.resample("MS").mean().dropna()


def load_real(sentiment_id="UMCSENT", stress_id="STLFSI4", refresh=False):
    sent = to_monthly(fetch_fred(sentiment_id, refresh))
    stress = to_monthly(fetch_fred(stress_id, refresh))
    return sent, stress


def make_synthetic(n_months=420, seed=0):
    """Synthetic series with a PLANTED sentiment-leads-stress link.
    For smoke tests only. Not evidence of anything."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1990-01-01", periods=n_months, freq="MS")
    shock = rng.normal(size=n_months)
    sent = 80 + rng.normal(0, 1, n_months) * 1.0 + shock * 3
    stress = np.zeros(n_months)
    for t in range(1, n_months):
        stress[t] = 0.7 * stress[t - 1] - 0.6 * shock[t - 1] + rng.normal(0, 0.4)
    return pd.Series(sent, idx, name="sent"), pd.Series(stress, idx, name="stress")
