

# Addendum to the Phase 1, Stage 1 pre-registration
Date: 22 October 2026
Applies to: `PREREGISTRATION.md` v1.0 (the original text is not edited)
Status: **Written before any Phase 1 model was run.** No Phase 1 result had been seen when this addendum was written.

The original registration leaves a few implementation details open. They are fixed here so that they cannot be chosen after seeing results. None of them changes a registered setting.

## 1. Training rows
A forecast for any month in year *Y* uses a model fitted in January of *Y*. A training row for month *t'* is used only if its whole outcome window closed before January of *Y*, that is, *t'* + *h* is earlier than January *Y*. (This is one month stricter than the Phase 0 code.) The minimum is 84 usable training rows. Features need the first three months of stress data for the 3-month change, so the first training row is March 1994.

## 2. Stress episodes
An episode is a run of months with the monthly stress index above 0.5. Two runs separated by fewer than six months below 0.5 are merged into one episode. An episode **contributes to the evaluation period** if its first month falls in the evaluation period (the first forecast month through the last month with a complete outcome window).

## 3. Leave-one-episode-out
For each contributing episode, drop every evaluation month *t* from (episode start − *h* months) through the episode's last month. Those are the months whose outcome window touches the episode, plus the months inside it. Recompute the out-of-sample R² on the remaining months. The model is not refitted.

## 4. Verdict rules, in order
1. **Inconclusive** if fewer than four episodes contribute.
2. **Supported** if all three registered conditions hold (R² at least 0.02; 95% interval excludes zero; positive after dropping each episode, except at most one).
3. **Inconclusive** if the 95% interval includes both 0 and 0.02. The data then cannot distinguish a 0.02 improvement from none.
4. **Not supported** otherwise. This includes the case where conditions 1 and 2 hold but condition 3 fails, which is labelled "not supported: not robust to dropping episodes".

The report always prints the pass or fail result of each of the three registered conditions next to the verdict, so a reader can apply the original wording directly.

## 5. Bootstrap
The interval resamples evaluation months in overlapping blocks of 12 (random start positions, 1,000 resamples, seed 0), recomputes R² = 1 − MSE_B / MSE_A on each resample, and takes the 2.5th and 97.5th percentiles.

## 6. Robustness with other stress indexes
The NFCI and OFR index use different scales, so the 0.5 threshold does not transfer. These robustness checks are **not part of this run**. A threshold for each will be registered in a further addendum before they are run.
