# Pre-registration: Stage 2c
**Does bank credit growth improve forecasts of the change in the U.S. unemployment rate beyond an unemployment-only baseline?**

Author: Robert (Roy) Adeniyi Aderinmola
Version: 1.0 (DRAFT, not yet committed)
Date registered: [date of the git commit that adds this file]
Status: **No Stage 2c model has been run. This file must be committed before any Stage 2c code is written or run, and the code and results will be committed afterwards, in that order.**

## 1. Why this test
Stage 2a asked whether the excess bond premium improves forecasts of financial stress and was inconclusive. Stage 2b asked whether the same indicator improves forecasts of the 12-month change in the unemployment rate. Its registered primary result was inconclusive, and the apparent gain was concentrated in 2020-2021. Both used a market-price indicator of credit conditions. Stage 2c tests a **quantity** indicator from the supply side of credit: the growth of bank loans and leases, published by the Federal Reserve in its H.8 release. It asks the same question as Stage 2b, with the same baseline, sample, windows, episodes and decision rule, so that the two results can be compared directly. Stage 2c does not use the stress index.

## 2. Disclosures
- **This stage was added after the Stage 2a and Stage 2b results were seen.** It was chosen to extend the program from a price indicator to a quantity indicator of credit, using the same design as Stage 2b. It is not a replacement for Stages 2a or 2b, whose results stand as reported.
- **Choices carried over from Stage 2b because of what its results showed.** The 2020-2021 exclusion check is registered here because Stage 2b's gain was concentrated in those years. The Stage 2b leave-one-episode-out check did not detect that concentration, so the 2020-2021 exclusion is reported beside it and is given the weight stated in section 6.
- **The data have been looked at.** The unemployment history was read in full before Stage 2b. For the loan-growth series, the file contents and summary values were read when it was received (range, a few spot values around 2004, 2010, 2020 and 2023, and the latest four months). No forecast, regression or accuracy measure has been computed on it.
- **The series is revised.** The Federal Reserve benchmarks the weekly sample to quarter-end Call Reports, and current values can change. The latest four months in the file used here (July 3.8, August 9.2, September 7.8, October 8.9) differ in three of the four months from the figures in the 13 November 2026 release table (3.8, 9.0, 7.4, 9.4). The cause was not established, and the file as downloaded is used as it stands. **No real-time forecasting claim is made.**
- **Break adjustment is the Federal Reserve's.** The growth series is published break-adjusted, so no months are dropped or adjusted by the author for mergers, nonbank structure activity or accounting consolidations. The author has not verified the Federal Reserve's break dates and relies on the published adjustment.
- **The sample starts in 1973 to match Stage 2b, not because the data start then.** The loan-growth series begins in 1947 and unemployment in 1948. Using the earlier years would add recessions but would make the result incomparable with Stage 2b. This was decided from the dates alone, before any model was run.
- **Number of tests in this program.** Stages 1, 2a, 2b and this one each have a primary specification and several secondary ones. No adjustment is made for the number of tests, and secondary results are never presented as findings.
- The code will be developed with AI assistance. An independent technical review will be sought [reviewer to be named], and any review recorded in the repository.
- Indicators tested so far: consumer sentiment (Stage 1, no improvement), excess bond premium against stress-index outcomes (Stage 2a, inconclusive) and against unemployment (Stage 2b, inconclusive). Repo and funding indicators, cross-border banking data, and the persistence leads from Stages 2a and 2b will have their own registrations.

## 3. Data
| Item | Specification |
|---|---|
| Outcome and baseline series | Civilian unemployment rate, `UNRATE` (FRED), the same file as Stage 2b, downloaded 24 November 2026. SHA-256 `fb669461abc34e00324b940be6bad1c7f89117652f28587196a7b8bf4a9f56a1`. One blank value, October 2025, **not filled**. |
| Indicator | Federal Reserve H.8 series `B1020NCBCMG`: loans and leases in bank credit, all commercial banks, seasonally adjusted, annual growth rate, break adjusted, monthly, percent per year. Source file: the Federal Reserve Data Download Program XML package (`FRB_h8_xml.zip`, data file dated 20 November 2026), downloaded 24 November 2026. SHA-256 of the zip `839aaa7fbbe7317ed5d34e84a29d6757ba0e3a3c5322ed46b32bcbe39d3ff59f`. The series is extracted unchanged to `data/raw/H8_B1020NCBCMG_monthly.csv` (columns `month`, `loans_growth`), SHA-256 `65c9a718fa1eb9af95b63e74da4b32747d2f1d680d247a3c74197e4dfcf813ac`. The extracted series runs from February 1947 to October 2026 with no gaps; from January 1973 it has 646 months. |
| Episode dates | NBER-based recession indicator `USRECM`, the same file as Stage 2b. SHA-256 `23463db4e751eab4b9aa570b3070737a01cb0ebe119f29d751eb6cf940666850`. Recessions since 1973: 1973-11 to 1975-03, 1980-01 to 1980-07, 1981-07 to 1982-11, 1990-07 to 1991-03, 2001-03 to 2001-11, 2007-12 to 2009-06, 2020-02 to 2020-04. |
| Missing values | The October 2025 UNRATE value is blank and is not filled or interpolated. Any row for which an input feature or the outcome is missing is dropped. |
| Vintage | Current (revised) values, single download for each file. |
| Files not used | `TOTLL` (the unadjusted level series) and the quarterly growth file are in the repository for reference only and are not used in any model. |

## 4. Outcomes (fixed)
Same as Stage 2b. For month *t*:
- **Primary: ΔU(12)** = UNRATE in month *t*+12 minus UNRATE in month *t*, in percentage points.
- **Secondary: ΔU(6)** = UNRATE in month *t*+6 minus UNRATE in month *t*.

## 5. Models (fixed)
- **Baseline A:** ordinary least squares on the unemployment rate in month *t* and its 3-month change.
- **Model B:** A plus the loan-growth series `g` as published in month *t* (no smoothing and no standardization) and its 3-month change (*g* in month *t* minus *g* in month *t*-3).
- The 3-month changes are computed on each continuous series before merging. **Rows before April 1973 are not used**, so the sample matches Stage 2b exactly.
- Estimation: expanding window, re-fit each January. A training row for month *t'* is used only if *t'* + *h* is earlier than the January of the forecast year. **Minimum 60 usable training rows (primary). Minimum 84 (registered sensitivity check).**
- Expected first forecast, from dates alone and to be confirmed by the code: with 60 rows, January 1980 for ΔU(12) and January 1979 for ΔU(6); with 84 rows, January 1982 for ΔU(12) and January 1981 for ΔU(6). The last evaluation month for ΔU(12) is September 2025, because October 2025 is missing.
- The monthly annualized growth rate is noisy, and no smoothed or averaged version is tested. This is a stated limitation, not a tuning option.

## 6. Primary hypothesis and decision rule
**Primary specification (the only one that decides the headline conclusion):** ΔU(12), minimum 60 training rows, Model B versus Baseline A.

Metric: out-of-sample R² relative to the baseline, `1 - MSE_B / MSE_A`. The 95% interval resamples evaluation months in overlapping blocks of 12 (random start positions, 1,000 resamples, seed 0) and takes the 2.5th and 97.5th percentiles.

*Episodes:* each NBER recession (a run of `USRECM` = 1) is one episode, taken as published and not merged. An episode contributes if its first month falls inside the evaluation period. Expected contributing episodes under the primary setting, from dates alone: 1980, 1981-82, 1990-91, 2001, 2007-09 and 2020 (six).

*Leave-one-episode-out:* for each contributing episode, drop every evaluation month from (episode start - *h* months) through the episode's last month, recompute R² on the rest, without refitting.

*Verdict, applied in this order (same rule as Stages 1, 2a and 2b):*
1. **Inconclusive** if fewer than four episodes contribute.
2. **Supported** if R² is at least 0.02, the 95% interval excludes zero, and R² stays positive after dropping each episode except at most one.
3. **Inconclusive** if the 95% interval includes both 0 and 0.02.
4. **Not supported** otherwise (labelled "not supported: not robust to dropping episodes" if the first two conditions hold but the third fails).

The report prints each of the three conditions next to the verdict.

*Weight given to the 2020-2021 exclusion.* The verdict rule above is unchanged. But the headline sentence in the README, the release notes and any document citing this stage will state the 2020-2021 exclusion result next to the verdict. **If the primary specification is "Supported" but its R² excluding 2020-2021 is below 0.02 or its interval excluding 2020-2021 includes zero, the headline is that the result depends on the pandemic period.** This is registered in advance because the Stage 2b leave-one-episode-out check did not detect that concentration.

*Complementary test (does not change the verdict).* For every specification the report gives the Clark-West (2007) statistic: with *y* the realized outcome and *pA*, *pB* the two forecasts, form *d* = (y - pA)² - [(y - pB)² - (pA - pB)²] for each evaluation month and test whether its mean is greater than zero, using Newey-West (Bartlett kernel, bandwidth equal to *h*) standard errors. The one-sided p-value is taken from the standard normal distribution. If the verdict is "not supported" but the one-sided p-value is below 0.05, the report says so plainly.

## 7. Secondary and registered sensitivity analyses (all reported)
1. ΔU(6), with its own R², interval and Clark-West result. It does not change the headline.
2. **Training window of 84 rows** for both outcomes. If the 60-row and 84-row verdicts for the primary specification differ, the report states both, and the headline is that the result depends on the training window.
3. **Excluding the COVID period:** drop all evaluation months from January 2020 to December 2021 and recompute R², the interval and the Clark-West statistic.
4. Mean absolute error for both models.
5. Descriptive only: the correlation between loan growth and the unemployment rate, in levels and 3-month changes, and between loan growth and the excess bond premium over their common months. These are not used in any model.

Every result is reported in one table, including those showing no improvement.

## 8. Limitations stated in advance
- The baseline is deliberately simple (unemployment level and 3-month change). A "supported" verdict would show that loan growth adds information beyond past unemployment alone, not beyond everything known to forecasters.
- Six recessions is a small number of episodes. Results can be driven by one or two, and by the 2020-2021 period in particular.
- Loan growth may move with or after the cycle rather than before it. The test makes no claim of a leading relationship.
- The 12-month outcome windows overlap, which the bootstrap blocks and Newey-West errors are intended to handle but do not remove.
- Linear models only. Current revised data only. Total loans and leases only; components such as commercial and industrial loans are not tested.

## 9. Not part of this stage
Components of bank loans. Repo and funding indicators. The persistence leads from Stages 2a and 2b. BIS cross-border banking data. Stress-index outcomes. Recession-dummy outcomes. Each will be registered separately before it is run.

## 10. Reporting and changes
- All results, null or positive, are reported in the README with the commit hash of the code that produced them.
- Any change to this plan after registration is made as a new commit with the date and the reason, and the original text is not edited.
- If a data problem or code error is found, the fix and both versions of the result are reported.
