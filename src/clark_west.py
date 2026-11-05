"""EXPLORATORY: Clark-West (2007) test for the Phase 1, Stage 1 forecasts.

Added AFTER the Stage 1 results were seen, on the advice that comparisons of nested
models need this test. It does not change the registered Stage 1 verdict.
Newey-West (Bartlett kernel) standard errors, bandwidth = horizon h; one-sided p-value.
"""
import math
from pathlib import Path
import numpy as np
import pandas as pd

from data import load_real
from phase1 import SPECS, build_features, add_outcome, oos_forecasts, oos_r2

OUT = Path(__file__).resolve().parents[1] / "outputs"


def clark_west(res, h):
    d = (res.y - res.pA) ** 2 - ((res.y - res.pB) ** 2 - (res.pA - res.pB) ** 2)
    d = d.to_numpy()
    n = len(d)
    dm = d - d.mean()
    lrv = (dm @ dm) / n
    for k in range(1, h + 1):
        w = 1 - k / (h + 1)
        lrv += 2 * w * (dm[k:] @ dm[:-k]) / n
    se = math.sqrt(lrv / n)
    t = d.mean() / se
    p = 0.5 * math.erfc(t / math.sqrt(2))   # one-sided: H1 mean > 0
    return t, p


def main():
    sent, stress = load_real("UMCSENT", "STLFSI4")
    feat = build_features(sent, stress)
    rows = []
    for name, kind, h, primary in SPECS:
        df = add_outcome(feat, kind, h)
        res = oos_forecasts(df, h)
        t, p = clark_west(res, h)
        rows.append({"spec": name, "primary": primary, "oos_months": len(res),
                     "oos_r2_B_vs_A": round(float(oos_r2(res)), 4),
                     "clark_west_t": round(t, 3), "one_sided_p": round(p, 4)})
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "stage1_clark_west_exploratory.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
