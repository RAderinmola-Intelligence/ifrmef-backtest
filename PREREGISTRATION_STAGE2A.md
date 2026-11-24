# Pre-registration: Stage 2a
**Does the excess bond premium improve forecasts of the severity and persistence of U.S. financial stress beyond a stress-index baseline?**

Author: Robert (Roy) Adeniyi Aderinmola
Version: 1.0
Date registered: [date of the git commit that adds this file]
Status: **No Stage 2a model has been run. This file must be committed before any Stage 2a code is run, and the code and results will be committed afterwards, in that order.**

## 1. Why this test
Stage 1 found that consumer sentiment did not improve forecasts of the severity or persistence of stress (see README). Stage 2a tests a credit-market indicator. Raw corporate credit spreads are not a clean test, because credit spreads and yields are inputs to the stress index used as the outcome and baseline. The excess bond premium (EBP) is "a component of corporate bond credit spreads that is not directly attributable to expected default risk" and, in the words of its authors' note, "provides an effective measure of investor sentiment or risk appetite in the corporate bond market." This stage asks whether that component adds information about how severe and how persistent stress becomes, beyond the stress index itself.

## 2. Disclosures
- Stage 1 results and the full history of the stress series have been seen. This registration protects against specification search from now on. It does not make the design blind to history.
- The indicator was chosen after reviewing candidate series and after an outside reviewer suggested credit-market indicators. Raw credit spreads were set aside because of the overlap with the stress index described above. The overlap is not removed by using the EBP: the EBP is built from corporate bond spreads, so it is related to inputs of the stress index. Its correlation with the stress level will be reported (section 7).
- The EBP is a Federal Reserve staff research product, not an official statistical release. Its authors state that "the entire history of the EBP may revise each month," that in practice revisions "tend to be modest and concentrated in the most-recent months," and that beginning with the September 2026 release a small subset of bond characteristics comes from a different commercial data provider, with the methodology unchanged and data before September 2026 left unrevised. One download will be used for the whole analysis, and its download date recorded. No real-time forecasting claim will be made.
- The code was developed with AI assistance. An independent technical review will be sought [reviewer to be named], and any review recorded in the repository.
- The Stage 1 addendum was committed after its run. For this stage, every rule below is in this file, and this file will be committed before any run.
- The Clark–West test (section 6) was added to this design after Stage 1 was run, on the advice that nested-model forecast comparisons need it. A Clark–West statistic for Stage 1 will be computed and reported as an exploratory addition, labelled as added after the Stage 1 results were seen. It does not change the Stage 1 verdict.
- Indicators tested in this program so far: consumer sentiment (Stage 1, no improvement). This registration covers the EBP only. Repo and funding indicators, and cross-border banking data, will have their own registrations.

## 3. Data
| Item | Specification |
|---|---|
| Stress measure (outcome and baseline) | St. Louis Fed Financial Stress Index, `STLFSI4`, weekly, averaged to calendar months, as in Stage 1. Sample starts December 1993. |
| Indicator | Excess bond premium (EBP), monthly, from the Federal Reserve Board's CSV at https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv. The file was downloaded on 24 November 2026 (SHA-256 `caa16e06…6542c5`). It has four columns: `date`, `gz_spread`, `ebp`, `est_prob`, with 646 monthly rows, January 1973 to October 2026, no missing months and no blank values. **Only the `ebp` column is used.** `gz_spread` (a raw credit spread) is not used, for the overlap reason given in section 1, and `est_prob` (the Fed's own recession probability) is not used. Missing months, if any appear, are not filled in. |
| Vintage | Current (revised) values, single download. |

## 4. Outcomes (fixed, same as Stage 1)
For month *t* (information through the end of month *t*):
- **Severity(h)** = the maximum monthly stress index over months *t+1* to *t+h*, for h = 3 (primary) and h = 6.
- **Persistence(h)** = the number of months in *t+1* to *t+h* with the stress index above 0.5, for h = 6 and h = 12.

## 5. Models (fixed)
- **Baseline A:** ordinary least squares on the current stress index and its 3-month change (same as Stage 1).
- **Model B:** A plus the EBP level and its 3-month change. No standardization.
- Estimation: expanding window, re-fit each January. A training row for month *t'* is used only if *t'* + *h* is earlier than the January of the forecast year. Minimum **84 usable training rows**. Forecasts begin in January 2002 (2003 for Persistence(12)).

## 6. Primary hypothesis and decision rule
**Primary specification (the only one that decides the headline conclusion):** Severity(3), STLFSI4, Model B versus Baseline A.

Metric: out-of-sample R² relative to the baseline, `1 - MSE_B / MSE_A`. The 95% interval resamples evaluation months in overlapping blocks of 12 (random start positions, 1,000 resamples, seed 0) and takes the 2.5th and 97.5th percentiles.

*Stress episodes:* runs of months with the monthly stress index above 0.5; runs separated by fewer than six months below 0.5 are merged. An episode contributes to the evaluation period if its first month falls inside it.

*Leave-one-episode-out:* for each contributing episode, drop every evaluation month from (episode start - *h* months) through the episode's last month, recompute R² on the rest, without refitting.

*Verdict, applied in this order:*
1. **Inconclusive** if fewer than four episodes contribute.
2. **Supported** if R² is at least 0.02, the 95% interval excludes zero, and R² stays positive after dropping each episode except at most one.
3. **Inconclusive** if the 95% interval includes both 0 and 0.02.
4. **Not supported** otherwise (labelled "not supported: not robust to dropping episodes" if the first two conditions hold but the third fails).

The report prints each of the three conditions next to the verdict.

*Complementary test (does not change the verdict).* Model B contains Baseline A, so out-of-sample R² is biased downward by estimation noise in the extra parameters. For every specification, the report also gives the Clark–West (2007) statistic: with *y* the realized outcome and *pA*, *pB* the two forecasts, form *d* = (y - pA)² - [(y - pB)² - (pA - pB)²] for each evaluation month, and test whether its mean is greater than zero, using Newey–West (Bartlett kernel, bandwidth equal to *h*) standard errors to allow for overlapping outcome windows. The one-sided p-value is taken from the standard normal distribution. The verdict above is decided by the registered rule alone. If the verdict is "not supported" but the Clark–West one-sided p-value is below 0.05, the report will say so plainly: the indicator carries some statistical information about the outcome that does not meet the registered standard for improving forecasts. If the verdict is "supported", the Clark–West result is reported as a consistency check.

## 7. Secondary and descriptive analyses (all reported)
Severity(6), Persistence(6), Persistence(12), mean absolute error, and the Clark–West statistic and one-sided p-value for each specification. Descriptive only: the correlation between the EBP and the stress index, to show how much of the EBP is already in the baseline. These do not change the headline conclusion. Every result is reported in one table, including those showing no improvement.

## 8. Not part of this stage
Raw credit spreads (overlap with the stress index inputs; the FRED high-yield spread series also now carries only three years of history). Repo and funding indicators. BIS cross-border banking data. The OFR Financial Stress Index as an alternative outcome, which needs its own registered threshold. Each will be registered separately before it is run.

## 9. Reporting and changes
- All results, null or positive, are reported in the README with the commit hash of the code that produced them.
- Any change to this plan after registration is made as a new commit with the date and the reason, and the original text is not edited.
- If a data problem or code error is found, the fix and both versions of the result are reported.
