# BharatStock AI — V111 Model Evaluation Guide

## What is new?

The project now reports two related but distinct research views:

1. **Binary direction benchmark:** predicts whether the executable three-bar return is positive or non-positive. This remains for comparison with earlier project versions.
2. **Cost-aware three-class benchmark:** predicts DOWN, NO_TRADE, or UP. It labels a direction only when the executable return exceeds the configured round-trip cost proxy. Returns inside the cost band are labelled NO_TRADE.

## How to run the experiment

Use the existing endpoint from PowerShell after the V111 API has been rebuilt:

```powershell
$result = Invoke-RestMethod "http://localhost:8000/api/research/intraday/%5ENSEI?instrument_key=NSE_INDEX%7CNifty%2050&interval=5&folds=3&cost_bps=10"
$result | ConvertTo-Json -Depth 35 | Out-File ".\AI-INTRADAY-RESEARCH-V111-RESULT.json" -Encoding utf8
$result.evaluation.three_class_evaluation.model_comparison | Format-Table -AutoSize
```

The three-class section is available at `evaluation.three_class_evaluation`.

## How to explain the classes

- DOWN: expected research label is a return below -20 bps when `cost_bps=10`.
- NO_TRADE: executable return lies from -20 bps through +20 bps.
- UP: expected research label is a return above +20 bps.

The threshold is calculated from the user's cost input: round-trip basis points = `2 × cost_bps`.

## How to interpret the metrics

- Accuracy: share of all test rows classified correctly.
- Balanced accuracy: average recall across classes; useful when class counts differ.
- Macro F1: gives each class equal weight.
- Confusion matrix: shows which classes the model confuses.
- Multiclass Brier score and log loss: evaluate probability quality; lower is better.
- Majority-class baseline: reference that predicts the most common training class.

A model should not be called useful merely because accuracy is high. Compare it with the baseline, inspect every fold, and check whether the NO_TRADE class is being identified. The three-class experiment does not enable trading.

## Current limitations

- News features can remain neutral when no timestamp-matched news records exist.
- The cost band is a research proxy, not a full brokerage/tax/slippage calculator.
- A few folds of recent candles are not enough to establish stable future performance.
- LSTM/GRU are separate optional models and are not claimed as trained by this update.
