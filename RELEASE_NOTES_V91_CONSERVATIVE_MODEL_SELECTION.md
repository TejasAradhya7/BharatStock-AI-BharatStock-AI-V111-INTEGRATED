# BharatStock AI V91 — Conservative chronological model selection

## Why this change
Earlier evaluation showed that the RF + Extra Trees ensemble's walk-forward accuracy was below the fold-trained majority baseline. Logistic Regression was close to baseline, but no candidate had demonstrated a reliable predictive edge. Choosing the numerically highest historical score alone would overfit model selection.

## Code changes
- Added `walk_forward.selection_recommendation` to the model evaluation response.
- A candidate is shortlisted only when it has at least five evaluated chronological folds, mean accuracy at least 1 percentage point above the fold-trained majority baseline, and mean balanced accuracy of at least 0.50.
- If no candidate clears all gates, the API explicitly returns `NO_CANDIDATE_CLEARED_BASELINE_GATE`.
- The recommendation never changes the production prediction model. Any shortlisted candidate still requires a new future-period confirmation before promotion.
- Added a regression test for the selection contract and the no-auto-promotion rule.

## Important limitations
- This is a model-selection guardrail and audit improvement, not a claim of higher accuracy.
- Existing historical data and previously inspected holdout are not fresh independent evidence.
- The current production learner remains RF + Extra Trees; no accuracy gain is claimed.
- No real-money trading readiness or profitability is implied.

## Verification
Run from `services/api`:

```powershell
python -m pytest tests/test_analysis.py -q
python -m pytest tests -q
```

Then rebuild the web app from `apps/web` with `npm ci` and `npm run build`.
