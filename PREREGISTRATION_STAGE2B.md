# Pre-registration: Stage 2b
**Does the excess bond premium improve forecasts of the change in the U.S. unemployment rate beyond an unemployment-only baseline?**

Author: Robert (Roy) Adeniyi Aderinmola
Version: 1.0
Date registered: [date of the git commit that adds this file]
Status: **No Stage 2b model has been run. This file must be committed before any Stage 2b code is written or run, and the code and results will be committed afterwards, in that order.**

## 1. Why this test
Stage 2a asked whether the excess bond premium (EBP) improves forecasts of the severity and persistence of financial stress, as measured by the St. Louis Fed Financial Stress Index. The primary test was inconclusive. That outcome is a hard target: the stress index is built from 18 market series and already contains much of the information in credit-market measures. Published work on the EBP is mostly about real-economy outcomes. A Federal Reserve staff note (Favara, Gilchrist, Lewis and Zakrajšek, FEDS Notes, 2016) links the EBP to the probability of a recession within 12 months, and Gilchrist and Zakrajšek (American Economic Review, 2012) find that the EBP drives the power of credit spreads to predict economic activity. Those results are in-sample. Stage 2b asks whether the EBP improves **out-of-sample** forecasts of the real-economy cost of financial stress, measured as the change in the unemployment rate over the next 12 months, beyond the unemployment rate itself.

## 2. Disclosures
- **This stage was added after Stage 2a results were seen.** It was chosen from the published literature above, after Stage 2a's primary test was inconclusive. It was not part of the original plan. It is not a replacement for Stage 2a, and Stage 2a's results stand as reported.
- **The training window differs from Stages 1 and 2a, and the reason is stated here before any run.** Stages 1 and 2a require at least 84 usable training rows. Applied here, that rule leaves exactly four recessions in the evaluation period, the minimum the verdict rule allows, and leaves the leave-one-episode-out check almost uninformative. This stage therefore uses **60** rows as the primary setting and reports **84** as a registered sensitivity check. This was decided from the count of episodes under each setting, calculated from dates alone, before any model was run.
- **The unemployment history has been seen.** The UNRATE file was read in full when it was received, so the 2020 spike and the general shape of the series are known. No forecast, regression or accuracy measure has been computed on it. The registered 2020 sensitivity check (section 7) follows from knowing about that spike.
- The EBP is a Federal Reserve staff research product. Its authors state that the entire history may revise each month and that revisions tend to be modest and concentrated in the most recent months. The same downloaded file is used as in Stage 2a. Its checksum is recorded below.
- UNRATE is seasonally adjusted and may be revised. Current values from a single download are used. **No real-time forecasting claim is made.**
- The code will be developed with AI assistance. An independent technical review will be sought [reviewer to be named], and any review recorded in the repository.
- The persistence leads seen in Stage 2a (positive point estimates, intervals including zero) are **not** tested here. They need their own registration.
- Indicators tested in this program so far: consumer sentiment (Stage 1, no improvement), excess bond premium against stress-index outcomes (Stage 2a, inconclusive). Repo and funding indicators, bank credit growth, and cross-border banking data will have their own registrations.

## 3. Data
| Item | Specification |
|---|---|
| Outcome and baseline series | Civilian unemployment rate, `UNRATE` (FRED, Bureau of Labor Statistics), monthly, seasonally adjusted, percent. File downloaded 24 November 2026. SHA-256 `fb669461abc34e00324b940be6bad1c7f89117652f28587196a7b8bf4a9f56a1`. 946 monthly rows, January 1948 to October 2026, no gaps in dates. **One blank value: October 2025.** |
| Indicator | Excess bond premium, `ebp` column only, from the Federal Reserve Board's CSV. The same file as Stage 2a, downloaded 24 November 2026. SHA-256 `caa16e0619cb5399b9c8f44433868351f01973f9594c50a4f1f87dd0856542c5`. 646 monthly rows, January 1973 to October 2026. |
| Episode dates | NBER-based recession indicator `USRECM` (FRED), monthly. File downloaded 24 November 2026. SHA-256 `23463db4e751eab4b9aa570b3070737a01cb0ebe119f29d751eb6cf940666850`. Its recession months since 1973 were checked against the NBER business-cycle table and match: 1973-11 to 1975-03, 1980-01 to 1980-07, 1981-07 to 1982-11, 1990-07 to 1991-03, 2001-03 to 2001-11, 2007-12 to 2009-06, 2020-02 to 2020-04. |
| Missing value | The October 2025 UNRATE value is blank. **It is not filled or interpolated.** Any row for which an input feature or the outcome is missing is dropped. This removes only the rows that depend on that month. |
| Vintage | Current (revised) values, single download for each file. |

## 4. Outcomes (fixed)
For month *t* (information through the end of month *t*):
- **Primary: ΔU(12)** = UNRATE in month *t*+12 minus UNRATE in month *t*, in percentage points.
- **Secondary: ΔU(6)** = UNRATE in month *t*+6 minus UNRATE in month *t*.

## 5. Models (fixed)
- **Baseline A:** ordinary least squares on the unemployment rate in month *t* and its 3-month change (month *t* minus month *t*−3).
- **Model B:** A plus the EBP level and its 3-month change. No standardization.
- The unemployment and EBP 3-month changes are computed on each continuous series before merging.
- Estimation: expanding window, re-fit each January. A training row for month *t'* is used only if *t'* + *h* is earlier than the January of the forecast year. **Minimum 60 usable training rows (primary). Minimum 84 (registered sensitivity check).**
- Expected first forecast, from dates alone and to be confirmed by the code: with 60 rows, January 1980 for ΔU(12) and January 1979 for ΔU(6); with 84 rows, January 1982 for ΔU(12) and January 1981 for ΔU(6). The last evaluation month for ΔU(12) is September 2025, because October 2025 is missing.

## 6. Primary hypothesis and decision rule
**Primary specification (the only one that decides the headline conclusion):** ΔU(12), minimum 60 training rows, Model B versus Baseline A.

Metric: out-of-sample R² relative to the baseline, `1 - MSE_B / MSE_A`. The 95% interval resamples evaluation months in overlapping blocks of 12 (random start positions, 1,000 resamples, seed 0) and takes the 2.5th and 97.5th percentiles.

*Episodes:* each NBER recession (a run of `USRECM` = 1) is one episode, taken as published and **not merged** with any other. An episode contributes if its first month falls inside the evaluation period. Expected contributing episodes under the primary setting, from dates alone: 1980, 1981–82, 1990–91, 2001, 2007–09 and 2020 (six).

*Leave-one-episode-out:* for each contributing episode, drop every evaluation month from (episode start − *h* months) through the episode's last month, recompute R² on the rest, without refitting.

*Verdict, applied in this order (same rule as Stages 1 and 2a):*
1. **Inconclusive** if fewer than four episodes contribute.
2. **Supported** if R² is at least 0.02, the 95% interval excludes zero, and R² stays positive after dropping each episode except at most one.
3. **Inconclusive** if the 95% interval includes both 0 and 0.02.
4. **Not supported** otherwise (labelled "not supported: not robust to dropping episodes" if the first two conditions hold but the third fails).

The report prints each of the three conditions next to the verdict.

*Complementary test (does not change the verdict).* For every specification the report also gives the Clark–West (2007) statistic: with *y* the realized outcome and *pA*, *pB* the two forecasts, form *d* = (y − pA)² − [(y − pB)² − (pA − pB)²] for each evaluation month, and test whether its mean is greater than zero, using Newey–West (Bartlett kernel, bandwidth equal to *h*) standard errors. The one-sided p-value is taken from the standard normal distribution. If the verdict is "not supported" but the one-sided p-value is below 0.05, the report says so plainly.

## 7. Secondary and registered sensitivity analyses (all reported)
1. ΔU(6), with its own R², interval and Clark–West result. It does not change the headline.
2. **Training window of 84 rows** for both outcomes. Under 84 rows, ΔU(12) is expected to have exactly four contributing episodes (1990, 2001, 2007–09, 2020), so its verdict rests on the minimum allowed. **If the 60-row and 84-row verdicts for the primary specification differ, the report states both, and the headline is that the result depends on the training window.**
3. **Excluding the COVID period:** drop all evaluation months from January 2020 to December 2021 and recompute R², the interval and the Clark–West statistic. The unemployment rate rose from 3.5% to 14.8% within two months in 2020, and squared forecast errors from those months may dominate the result.
4. Mean absolute error for both models.
5. Descriptive only: the correlation between the EBP and the unemployment rate, in levels and 3-month changes.

Every result is reported in one table, including those showing no improvement.

## 8. Limitations stated in advance
- The baseline is deliberately simple (unemployment level and 3-month change). It is easier to beat than a baseline that includes the yield curve or other financial variables, so a "supported" verdict would show the EBP adds information beyond past unemployment alone, not beyond everything known to forecasters.
- Six recessions is a small number of episodes, and the results can be driven by one or two of them.
- The 12-month outcome windows overlap, which the bootstrap blocks and Newey–West errors are intended to handle but do not remove.
- Linear models only. Current revised data only.

## 9. Not part of this stage
Bank credit growth and other indicators. Repo and funding indicators. The persistence leads from Stage 2a. BIS cross-border banking data. Recession-dummy outcomes (NBER dates are announced with a delay). Each will be registered separately before it is run.

## 10. Reporting and changes
- All results, null or positive, are reported in the README with the commit hash of the code that produced them.
- Any change to this plan after registration is made as a new commit with the date and the reason, and the original text is not edited.
- If a data problem or code error is found, the fix and both versions of the result are reported.
