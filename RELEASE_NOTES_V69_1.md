# BharatStock AI V69.1

- Updated the experimental prediction model to retrain a Random Forest + Extra Trees soft-voting ensemble on the latest available historical dataset for each prediction request.
- Preserved chronological holdout and expanding-window walk-forward evaluation.
- Combined tree feature importance for model explanation.
- Clarified retraining timing and research-only limitations.
- Backend tests: 84 passed, 1 existing deprecation warning.

This does not guarantee higher predictive accuracy or mean the model learns from tomorrow's result before that result exists. Live quote coverage depends on configured Upstox instrument mappings and valid API authorization.
