# ifrmef-backtest

A small, reproducible back-test of one question behind early-warning analytics for financial stability:

> Does consumer sentiment add **out-of-sample** information for warning of the onset of financial stress, beyond what the stress index itself already shows?

This is a prototype built on public data. It tests one indicator against one stress measure. It is not a claim that any framework works.

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
PREREGISTRATION.md was committed before any Phase 1 model was run. PREREGISTRATION_ADDENDUM.md, which fixes implementation details, was written before the run but committed afterwards, together with the code, so the repository’s timestamps cannot confirm its timing.”
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

Full tables: `outputs/phase1_results_real.csv`, `outputs/phase1_leave_one_episode_out_real.csv`, `outputs/phase1_episodes_real.csv`. Chart: `outputs/phase1_primary_real.png`.

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

## License
MIT. See `LICENSE`.

