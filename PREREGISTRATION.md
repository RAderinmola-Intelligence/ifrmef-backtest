# Pre-registration: Phase 1, Stage 1
**Severity and persistence of U.S. financial stress: does consumer sentiment improve forecasts beyond a stress-index baseline?**

Author: Robert (Roy) Adeniyi Aderinmola
Version: 1.0
Date registered: [22 October 2026]
Status: **No Phase 1 model has been run. This file must be committed before any Phase 1 code is run.**

## 1. Why this test
Phase 0 (see README) found no evidence that consumer sentiment improves out-of-sample warning of stress *onset*. Onsets such as early 2020 are largely shocks. This stage asks about vulnerabilities instead: once conditions are stressed or fragile, do sentiment indicators help forecast how severe and how persistent stress becomes?

## 2. Disclosures
- Phase 0 results and the full history of both series have been seen. Thresholds below were chosen after seeing, in Phase 0, the share of months above each one. This registration protects against specification search from now on. It does not make the design blind to history.
- The Phase 0 code was developed with AI assistance. Phase 1 code will be reviewed by an independent technical partner [to be named] where possible, and any review will be recorded in the repository.
- Two design parameters, the 0.5 episode threshold and the 84-month minimum training window, were set after counting stress episodes in the data and **before any Phase 1 model was run**. With a 1.0 threshold and a 120-month window, the evaluation period would contain only two episodes, which would make the primary test inconclusive by construction.
- This registration covers **Stage 1 only (sentiment)**. Later stages (credit, funding and exposure indicators) will have separate registrations committed before they are run.

## 3. Data
| Item | Specification |
|---|---|
| Stress measure (primary) | St. Louis Fed Financial Stress Index, `STLFSI4`, weekly, averaged to calendar months. Sample starts December 1993. |
| Sentiment | University of Michigan Consumer Sentiment, `UMCSENT`, monthly, continuous from January 1978. |
| Robustness stress measures | Chicago Fed NFCI and OFR Financial Stress Index, if obtainable. Start dates and revision behavior to be confirmed and recorded. |
| Vintage | Current (revised) values. Results will be labeled as such. ALFRED vintages cover only recent years for STLFSI4, so no real-time claim will be made. |

## 4. Outcomes (fixed)
For month *t* (information through the end of month *t*):
- **Severity(h)** = the maximum monthly stress index over months *t+1* to *t+h*, for h = 3 (primary) and h = 6.
- **Persistence(h)** = the number of months in *t+1* to *t+h* with the stress index above 0.5, for h = 6 and h = 12.

All months are used (not only months below a stress threshold).

## 5. Models (fixed)
- **Baseline A:** ordinary least squares on the current stress index and its 3-month change.
- **Model B:** A plus sentiment z-score (10-year rolling) and 3-month change in sentiment. Sentiment features are built on the full continuous sentiment history before merging.
- Estimation: expanding window, re-fit annually. Training rows are used only if their outcome window closed before the forecast month. Minimum **84 months** of training data, so forecasts begin in 2002.

## 6. Primary hypothesis and decision rule
**Primary specification (the only one that decides the headline conclusion):** Severity(3), STLFSI4, Model B versus Baseline A.

Metric: out-of-sample R² relative to the baseline, `1 - MSE_B / MSE_A`.

**Supported** only if all hold:
1. Out-of-sample R² is at least **0.02**.
2. The 95% block-bootstrap interval (block length 12 months, 1,000 resamples, seed 0) excludes zero.
3. Leave-one-episode-out: R² remains positive after dropping each stress episode, except for at most one.

**Not supported** if condition 1 or 2 fails.

**Inconclusive** if fewer than four distinct stress episodes contribute to the evaluation period, or the interval is too wide to distinguish a 0.02 improvement from zero. This will be stated as inconclusive, not as support or refutation.

*Why 0.02:* a small positive threshold avoids treating noise as a finding. It is a fixed convention chosen before testing, not an estimate of economic significance.

*Stress episodes* are contiguous spells with the monthly index above **0.5**, separated by at least six months below it. In the current data this gives seven episodes in the full sample (starting 1998-09, 2000-12, 2007-08, 2010-05, 2011-08, 2016-01 and 2020-03), of which five start inside the evaluation period. They will be listed in the report.

## 7. Secondary analyses (exploratory, all reported)
Severity(6), Persistence(6), Persistence(12), mean absolute error, and robustness with the NFCI and the OFR index. These do not change the headline conclusion. Every result will be reported in one table, including those that show no improvement.

## 8. Reporting and changes
- All results, null or positive, are reported in the README with the commit hash of the code that produced them.
- Any change to this plan after registration is made as a new commit with the date and the reason, and the original text is not edited.
- If a data problem or code error is found, the fix and both versions of the result are reported, as in Phase 0.
