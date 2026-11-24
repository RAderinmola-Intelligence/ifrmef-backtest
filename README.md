# ifrmef-backtest

A small, reproducible back-test of one question behind early-warning analytics for financial stability:

> Does consumer sentiment add **out-of-sample** information for warning of the onset of financial stress, beyond what the stress index itself already shows?

This is a prototype built on public data. It tests one indicator against one stress measure. It is not a claim that any framework works.

## Status at a glance
- **Phase 0 (onset of stress):** no evidence that consumer sentiment helps; low power. See Results.
- **Phase 1, Stage 1 (pre-registered; severity and persistence of stress):** sentiment did not help. Primary test: out-of-sample R² -0.058 (95% interval -0.221 to -0.029). See Phase 1 results.
- **Phase 1, Stage 2a (pre-registered; excess bond premium):** no improvement in the primary test. Out-of-sample R² -0.029 (95% interval -0.103 to 0.025), inconclusive by the registered rule. See Stage 2a results.
- **Phase 1, Stage 2b (pre-registered; excess bond premium and unemployment):** inconclusive. Out-of-sample R² 0.233 (95% interval -0.100 to 0.359); about 97% of the gain falls in 2020 and 2021. See Stage 2b results.
- **Phase 1, Stage 2c (pre-registered; bank loan growth and unemployment):** not supported. Out-of-sample R² -0.079 (95% interval -0.143 to -0.031); loan growth made forecasts worse. See Stage 2c results.
- **Next:** repo and funding indicators and cross-border banking data, each registered before it is run.
- **Author:** Robert (Roy) Aderinmola, https://www.linkedin.com/in/roy-aderinmola-1aa27944/. 

## Why this question
Official data used to monitor financial risk are often reported with a lag. For example, the Federal Reserve's May 2026 Financial Stability Report notes that hedge fund data from Form PF are reported on a two-quarter lag. Higher-frequency indicators are one way to add earlier information. This repo tests whether one such indicator, consumer sentiment, does.

## Design
| Item | Choice |
|---|---|
| Sentiment | University of Michigan Consumer Sentiment (`UMCSENT`, FRED), monthly |
| Stress | St. Louis Fed Financial Stress Index (`STLFSI4`, FRED), weekly averaged to monthly |
| Sample | Months not already in stress (stress index at or below the threshold), so the test is of *onset* |
| Target | Stress index exceeds the threshold in any of the next `H` months (default `H=3`, threshold `1.0`) |
| Model A | Logistic regression on current stress level and its 3-month change |
| Model B | Model A plus sentiment z-score (10-year rolling) and 3-month change in sentiment |
| Validation | Expanding window. Each year's forecasts use only models fit on data whose outcome window had closed before that year |
| Metric | Out-of-sample AUC (A vs B), Brier score, and a block-bootstrap 95% interval for the AUC difference |

The threshold, horizon and series are command-line options. Report the base rate and number of onset events with any result.

## Pre-registered settings
To avoid choosing a flattering setting after seeing results, the horizons (3, 6 and 12 months) and thresholds (0.5, 1.0, 1.5 for STLFSI4) are fixed here before the first real run. `python backtest.py --grid` runs all combinations and reports every one, including those where sentiment adds nothing. Any later change to this grid must be recorded in the repository history with the reason.

## Run it
```bash
pip install -r requirements.txt
cd src
python backtest.py                              # real data from FRED
python backtest.py --horizon 6 --threshold 0.5  # variants
python backtest.py --grid                       # all pre-registered settings
python backtest.py --stress NFCI --threshold 0 # robustness: Chicago Fed NFCI
python phase1.py                                # Phase 1, Stage 1 (pre-registered)
python stage2a.py                               # Phase 1, Stage 2a (pre-registered; needs data/raw/ebp_csv.csv)
python stage2b.py                               # Phase 1, Stage 2b (pre-registered; needs data/raw/ebp_csv.csv, UNRATE.csv and USRECM.csv)
python stage2c.py                               # Phase 1, Stage 2c (pre-registered; needs data/raw/H8_B1020NCBCMG_monthly.csv, UNRATE.csv and USRECM.csv)
cd .. && pytest                                 # tests (synthetic data)
```
Outputs go to `outputs/`: out-of-sample predictions (CSV) and a probability chart (PNG).

## Results
Run on 22 October 2026 with FRED downloads of `UMCSENT` (to Aug 2026) and `STLFSI4` (to 9 Oct 2026), using the pre-registered grid above. Data are current (revised) values.

**Code fix between runs.** The first run computed the sentiment rolling window after merging with the stress series (which starts in 1993), which dropped the 1998, 2001 and 2002 episodes and left only 7 onset months. I fixed this so sentiment features use the full sentiment history before merging, and re-ran. The change was made because of that sample problem, not because of the direction of any result. The first run's numbers are not used. In it, sentiment also did not improve on the baseline in any of the nine settings.

| Horizon (months) | Threshold | OOS months | Onset months | AUC A (stress only) | AUC B (+ sentiment) | B minus A | 95% interval |
|---|---|---|---|---|---|---|---|
| 3 | 0.5 | 195 | 15 | 0.514 | 0.477 | -0.037 | (-0.298, 0.169) |
| 3 | 1.0 | 233 | 7 | 0.540 | 0.474 | -0.066 | (-0.177, -0.002) |
| 3 | 1.5 | 206 | 7 | 0.298 | 0.448 | +0.150 | (-0.23, 0.511) |
| 6 | 0.5 | 192 | 30 | 0.551 | 0.510 | -0.041 | (-0.249, 0.11) |
| 6 | 1.0 | 218 | 13 | 0.472 | 0.379 | -0.093 | (-0.231, -0.013) |
| 6 | 1.5 | 203 | 10 | 0.312 | 0.272 | -0.040 | (-0.493, 0.236) |
| 12 | 0.5 | 186 | 51 | 0.462 | 0.338 | -0.124 | (-0.215, -0.068) |
| 12 | 1.0 | 212 | 25 | 0.360 | 0.342 | -0.018 | (-0.076, 0.014) |
| 12 | 1.5 | 197 | 16 | 0.365 | 0.176 | -0.189 | (-0.421, 0.018) |

**Reading.**
- Across all nine pre-registered settings, adding sentiment did **not** improve out-of-sample AUC. Differences are negative in eight of nine and positive in one (+0.150), and that one has a wide interval (-0.23 to 0.51). Several intervals exclude zero on the negative side.
- The baseline itself (stress level and change) has AUC near or below 0.5 in most settings. Stress onset is not predictable from these inputs in this design.
- The test has very low power. Out-of-sample forecasts start in 2005, and the stress episodes in that period are essentially 2007 to 2008 and early 2020. Two episodes cannot support a firm conclusion in either direction.
  
- **Conclusion: no evidence that consumer sentiment adds information for warning of stress onset beyond the stress index in this design. The result is inconclusive for the broader question.**

**Interpretation and next step.** Onsets such as early 2020 are largely exogenous shocks, which the Federal Reserve's framework treats as hard to forecast, in contrast to vulnerabilities, which can be monitored as they build. A better-posed test may be whether sentiment and other indicators help predict the *severity or persistence* of stress once a shock occurs, which is what vulnerabilities affect. That is a new design and will be pre-registered in this repository before it is run, and results will be reported alongside this one.

## Phase 1, Stage 1 results (pre-registered)
`PREREGISTRATION.md` was committed before any Phase 1 model was run. `PREREGISTRATION_ADDENDUM.md`, which fixes implementation details, was written before the run but committed afterwards, together with the code, so the repository's timestamps cannot confirm its timing.
Code: `src/phase1.py`. Run once, on the data in `data/raw` (UMCSENT to August 2026; STLFSI4 to October 2026, current revised values). Settings were not changed after seeing results.

Question: does adding consumer sentiment to a stress-index baseline improve out-of-sample forecasts of how severe and how persistent U.S. financial stress becomes? Metric: out-of-sample R² of model B (stress + sentiment) relative to baseline A (stress only), `1 - MSE_B / MSE_A`. Negative means sentiment made forecasts worse.

| Specification | Role | OOS R² (B vs A) | 95% block-bootstrap interval | Verdict |
|---|---|---|---|---|
| Severity(3) | **Primary** | -0.058 | -0.221 to -0.029 | **Not supported** |
| Severity(6) | Secondary | -0.148 | -0.334 to -0.095 | Not supported |
| Persistence(6) | Secondary | -0.189 | -0.493 to 0.126 | Inconclusive |
| Persistence(12) | Secondary | -0.179 | -0.475 to 0.072 | Inconclusive |

For the primary specification: 293 forecast months (January 2002 on), five stress episodes in the evaluation period (2007-08, 2010-05, 2011-08, 2016-01, 2020-03). R² stayed negative after dropping each episode in turn (-0.073 to -0.057). Mean absolute error was also higher for B (0.462) than for A (0.437).

**Reading.** In this design, consumer sentiment did not improve forecasts of the severity of stress beyond the stress index. For Severity(3) and Severity(6), the interval lies below zero: the added sentiment terms made out-of-sample forecasts worse, most likely because they add estimation noise. This is a negative result for this one indicator, this stress index, this sample and linear models. It says nothing about credit, funding or exposure indicators, which later stages will test under their own registrations. Persistence results are inconclusive by the registered rule (their intervals include both 0 and 0.02), although every point estimate is negative.

**Not done.** Robustness with the NFCI and OFR indexes was not run. Their scales differ and a threshold for each has to be registered first (see the addendum). All data are current revised values, not real-time vintages, so nothing here is a real-time forecasting claim. The Phase 1 code was written with AI assistance and has not yet had independent technical review.

**Exploratory addition.** After the results were seen, a Clark–West test was run on the Stage 1 forecasts (`src/clark_west.py`, results in `outputs/stage1_clark_west_exploratory.csv`). One-sided p-values are 0.91 (Severity(3)), 0.98 (Severity(6)), 0.48 (Persistence(6)) and 0.53 (Persistence(12)), so the null result is not an artifact of estimation noise in nested-model comparisons. This was added after the registered results were known and does not change the registered verdict.

Full tables: `outputs/phase1_results_real.csv`, `outputs/phase1_leave_one_episode_out_real.csv`, `outputs/phase1_episodes_real.csv`. Chart: `outputs/phase1_primary_real.png`.

## Phase 1, Stage 2a: excess bond premium (result: no improvement in the primary test)

Registered in `PREREGISTRATION_STAGE2A.md` (commit `4d729ef`, 24 November 2026) before any Stage 2a code was written or run. Code: `src/stage2a.py`, tests in `tests/test_stage2a.py`. Run once on the data in `data/raw`: the Federal Reserve Board's excess bond premium file downloaded 24 November 2026 (January 1973 to October 2026, 646 months, no gaps; only the `ebp` column is used) and `STLFSI4` to 9 October 2026, current revised values. Settings were not changed after seeing results. Code commit: `a8f86f8`.

Question: does the excess bond premium (its level and 3-month change) improve forecasts of how severe and how persistent U.S. financial stress becomes, beyond the stress index itself?

| Specification | R² of B vs A | 95% interval | Clark–West one-sided p | Registered verdict |
|---|---|---|---|---|
| **Severity(3) (primary)** | **-0.029** | -0.103 to 0.025 | 0.58 | **Inconclusive (interval includes both 0 and 0.02)** |
| Severity(6) | -0.038 | -0.058 to 0.022 | 0.83 | Inconclusive |
| Persistence(6) | 0.214 | -0.186 to 0.540 | 0.085 | Inconclusive |
| Persistence(12) | 0.149 | -0.278 to 0.400 | 0.066 | Inconclusive |

What this shows, in plain terms:
- **Primary test:** the excess bond premium did not improve the 3-month severity forecast. The point estimate is slightly negative (-0.029), the Clark–West test finds no evidence of a gain (p = 0.58), and the interval is too wide to rule out either zero or a small gain. Under the registered rule this is "inconclusive". It is not evidence of improvement.
- **Persistence specifications (secondary):** the point estimates are positive (0.21 and 0.15), but both intervals include zero, the Clark–West p-values (0.085 and 0.066) do not reach 0.05, and the gain falls sharply when the 2007–2009 episode is left out (0.21 to 0.10, and 0.15 to 0.05). With five stress episodes and four specifications tested, this is a lead to examine, not a finding. It does not change the headline conclusion.
- **Overlap with the stress index:** the excess bond premium and the stress index have a correlation of 0.83 in levels and 0.69 in 3-month changes (1994-03 to 2026-10). Much of the premium is already in the baseline, as expected.
- **Sample:** 295 forecast months for the primary specification (January 2002 to July 2026), five stress episodes. The last month of the stress series (October 2026) contains only two weekly readings. A check excluding it gives the same results (`outputs/stage2a_sensitivity_excluding_partial_october_2026.csv`); this check was added after the run and is exploratory.

Files: `outputs/stage2a_results_real.csv`, `stage2a_leave_one_episode_out_real.csv`, `stage2a_episodes_real.csv`, `stage2a_primary_forecasts_real.csv`, `stage2a_primary_real.png`, `stage2a_correlation_real.csv`, `stage2a_sensitivity_excluding_partial_october_2026.csv`.

## Phase 1, Stage 2b: excess bond premium and unemployment (result: inconclusive)

Registered in `PREREGISTRATION_STAGE2B.md` (commit `19e3181`, 24 November 2026) before any Stage 2b code was written or run. This stage was added after the Stage 2a results were seen, chosen from the published literature, and is labelled as such in the registration. Code: `src/stage2b.py`, tests in `tests/test_stage2b.py`. Run once on the data in `data/raw`: the same Federal Reserve Board excess bond premium file as Stage 2a, `UNRATE` (U.S. unemployment rate, seasonally adjusted, January 1948 to October 2026, one blank month, October 2025, which is dropped and not filled) and the NBER recession indicator `USRECM`, all downloaded 24 November 2026, current revised values. File checksums are recorded in the registration. Settings were not changed after seeing results. Code commit: `7e57e29`.

Question: does the excess bond premium (its level and 3-month change) improve out-of-sample forecasts of the change in the unemployment rate over the next 12 months, beyond the unemployment rate's own level and 3-month change?

| Specification | R² of B vs A | 95% interval | Clark–West one-sided p | Registered verdict |
|---|---|---|---|---|
| **ΔU(12), 60-row window (primary)** | **0.233** | -0.100 to 0.359 | 0.080 | **Inconclusive (interval includes both 0 and 0.02)** |
| ΔU(12), 84-row window | 0.230 | -0.194 to 0.359 | 0.093 | Inconclusive |
| ΔU(6), 60-row window | 0.209 | -0.159 to 0.329 | 0.075 | Inconclusive |
| ΔU(6), 84-row window | 0.214 | -0.168 to 0.338 | 0.078 | Inconclusive |

What this shows, in plain terms:
- **Primary test:** the point estimate is a 23% reduction in squared forecast error, but the 95% interval runs from -0.10 to 0.36, so it cannot rule out zero. Under the registered rule the verdict is "inconclusive". The Clark–West p-value (0.080) does not reach 0.05. Both training windows give the same verdict.
- **The gain is concentrated in 2020 and 2021.** The registered check excluding January 2020 to December 2021 gives R² = 0.016 for ΔU(12) (interval -0.164 to 0.204, Clark–West p = 0.031) and R² = -0.024 for ΔU(6) (Clark–West p = 0.010). In an exploratory breakdown made after the run, about 97% of the primary specification's total squared-error gain falls in those two years. Leaving out the 2020 recession alone, as the leave-one-episode-out check does, removes only the months up to April 2020 and does not show this.
- **Outside the pandemic years,** the model with the excess bond premium has slightly lower average errors, and the Clark–West test finds some evidence of a small gain. The gain is just below the registered 0.02 standard in the ΔU(12) case (0.016) and negative in the ΔU(6) case.
- **Overlap:** the excess bond premium and the unemployment rate have a correlation of 0.14 in levels and 0.08 in 3-month changes (1973-01 to 2026-10), so the premium carries information that is mostly separate from unemployment.
- **Sample:** 548 forecast months for the primary specification (January 1980 to September 2025), six recessions (1980, 1981–82, 1990–91, 2001, 2007–09, 2020). With the 84-row window there are four.
- **Limit:** the baseline is deliberately simple, so beating it would not show the premium adds information beyond what forecasters already use.

Files: `outputs/stage2b_results_real.csv`, `stage2b_sensitivity_real.csv`, `stage2b_leave_one_episode_out_real.csv`, `stage2b_episodes_real.csv`, `stage2b_primary_forecasts_real.csv`, `stage2b_primary_real.png`, `stage2b_correlation_real.csv`.

## Phase 1, Stage 2c: bank loan growth and unemployment (result: not supported)

Registered in `PREREGISTRATION_STAGE2C.md` (commit `b5a5454`, 24 November 2026) before any Stage 2c code was written or run. This stage was added after the Stage 2a and 2b results were seen and uses the same design as Stage 2b, so the two can be compared directly. Code: `src/stage2c.py`, tests in `tests/test_stage2c.py`. Run once on current revised data downloaded 24 November 2026: Federal Reserve H.8 series `B1020NCBCMG` (loans and leases in bank credit, all commercial banks, seasonally adjusted, annualized growth rate, break adjusted, monthly), extracted unchanged from the Federal Reserve's XML package to `data/raw/H8_B1020NCBCMG_monthly.csv`; the same `UNRATE` and `USRECM` files as Stage 2b. File checksums are recorded in the registration. The original XML package (about 80 MB) is not stored here. Settings were not changed after seeing results. Code commit: `94ef62c`.

Question: does bank loan growth (its level and 3-month change, as published, with no smoothing) improve out-of-sample forecasts of the change in the unemployment rate over the next 12 months, beyond the unemployment rate's own level and 3-month change?

| Specification | R² of B vs A | 95% interval | Clark–West one-sided p | Registered verdict |
|---|---|---|---|---|
| **ΔU(12), 60-row window (primary)** | **-0.079** | -0.143 to -0.031 | 0.93 | **Not supported** |
| ΔU(12), 84-row window | -0.077 | -0.108 to -0.015 | 0.92 | Not supported |
| ΔU(6), 60-row window | -0.028 | -0.156 to -0.012 | 0.99 | Not supported |
| ΔU(6), 84-row window | -0.028 | -0.171 to -0.012 | 0.99 | Not supported |

What this shows, in plain terms:
- **Primary test:** adding loan growth made the forecasts worse. Squared forecast error rose, and the 95% interval lies entirely below zero. The Clark–West test finds no evidence of a gain (p = 0.93). Both training windows and both horizons agree.
- **It does not depend on one episode.** R² stays negative when each of the six recessions is dropped in turn (-0.062 to -0.087), and when January 2020 to December 2021 is excluded (-0.073 for ΔU(12), -0.043 for ΔU(6)).
- **Overlap:** loan growth and the unemployment rate have a correlation of -0.26 in levels and 0.02 in 3-month changes (1973-04 to 2026-10). Loan growth and the excess bond premium have -0.12 in levels and 0.19 in 3-month changes (1973-01 to 2026-10). These are descriptive only.
- **Sample:** 548 forecast months for the primary specification (January 1980 to September 2025), six recessions (1980, 1981–82, 1990–91, 2001, 2007–09, 2020). The baseline error is identical to Stage 2b, as it should be, because the sample is the same.
- **Limits:** the monthly annualized growth rate is noisy and is used here without smoothing, so this result is for that form only. It does not show that bank credit has no value as an indicator. Published work suggests credit growth may matter more for the severity of downturns than for their timing, and a U.S.-only sample of six recessions is too small to test that. The baseline is deliberately simple. The series is revised by the Federal Reserve, and the latest months in the file differ from the 13 November release table.

Files: `outputs/stage2c_results_real.csv`, `stage2c_sensitivity_real.csv`, `stage2c_leave_one_episode_out_real.csv`, `stage2c_episodes_real.csv`, `stage2c_primary_forecasts_real.csv`, `stage2c_primary_real.png`, `stage2c_correlation_real.csv`, `stage2c_run_log.txt`.


## What the tests cover
The tests use synthetic data with a planted link, only to confirm that (1) features use no future information, (2) the pipeline runs end to end, and (3) it can detect a signal when one exists. Synthetic output is never a finding. The `--synthetic` flag is labeled accordingly.

## Limitations
- Few stress episodes in the sample, so intervals will be wide. Treat any difference with caution.
- Sentiment is a survey measure, not transaction or behavioral flow data. This tests the simplest version of the idea.
- Results depend on the stress threshold and horizon. Check that conclusions hold across several settings before drawing any.
- FRED serves current (revised) values, not what was known in real time. The St. Louis Fed notes that all data are subject to revision, and the Chicago Fed states that the history of the NFCI can change from week to week. Real-time vintages are archived in ALFRED, but for STLFSI4 they cover only recent years, so a full real-time test is not possible. Results use revised data and should be read as such.
- One stress index and one sentiment series. No claim is made about cross-border transmission or interconnection.

## Data
Public series from the Federal Reserve Bank of St. Louis (FRED). Check each series' terms of use. Data are downloaded at run time and not redistributed here.
The excess bond premium file is not on FRED. Download it from the Federal Reserve Board at https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv, save it as data/raw/ebp_csv.csv, and record the download date. The history of this file can be revised each month, so results depend on the download date.
The Stage 2b series are on FRED: UNRATE (https://fred.stlouisfed.org/series/UNRATE) and USRECM (https://fred.stlouisfed.org/series/USRECM). Download each as CSV, save them as data/raw/UNRATE.csv and data/raw/USRECM.csv, and record the download date. UNRATE has one blank month (October 2025), which the code drops and does not fill.
The Stage 2c series is Federal Reserve H.8 `B1020NCBCMG` (loans and leases in bank credit, all commercial banks, seasonally adjusted, annualized growth rate, break adjusted, monthly). It was extracted unchanged from the Federal Reserve Data Download Program XML package (H.8, downloaded 24 November 2026) and is stored in this repository as `data/raw/H8_B1020NCBCMG_monthly.csv` (columns `month`, `loans_growth`). The XML package itself is about 80 MB and is not stored here. Its checksum and the checksum of the extracted file are in `PREREGISTRATION_STAGE2C.md`. The Federal Reserve revises this series, so results depend on the download date.

## License
MIT. See `LICENSE`.
