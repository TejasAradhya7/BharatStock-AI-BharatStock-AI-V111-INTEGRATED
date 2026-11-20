# BharatStock AI — AI Model Completion & Results Report (V111)

**Evidence snapshot date:** 20 November 2026  
**Scope:** AI model, evaluation, and recorded V111 experimental results.  
**Model changes made for this completion package:** none. Existing model weights, feature definitions, labels, thresholds, and production selection policy are preserved. No accuracy target was forced.

## 1. Daily next-session direction model

The live daily prediction path uses the versioned `bharatstock-rf-et-v1` Random Forest + Extra Trees soft-voting ensemble with eight technical features. Its reported next-session target is whether the next close is above the current close.

### RELIANCE.NS API snapshot — 20 Nov 2026

| Measure | Recorded result |
|---|---:|
| Training observations | 1,187 |
| Walk-forward folds | 5 |
| Walk-forward test observations | 474 |
| Mean walk-forward accuracy | **44.94%** |
| Mean balanced accuracy | **45.15%** |
| Fold-trained majority baseline | **51.26%** |
| Accuracy gap vs baseline | **−6.33 percentage points** |
| Mean Brier score | 0.2596 |
| Mean log loss | 0.7129 |
| Validation status | `WEAK_BELOW_BASELINE` |

No candidate passed the baseline selection gate. Production remains on the established ensemble; no candidate was promoted. The 53.36% chronological holdout score (238 observations) is explicitly diagnostic only because this holdout was previously inspected; it is not fresh confirmatory evidence.

The latest prediction in this snapshot was DOWN with 50.92% model confidence (UP probability 49.08%). These are uncalibrated model outputs, not calibrated probabilities of profit.

### NIFTY 50 daily snapshot — 20 Nov 2026

A separate stored API snapshot for `^NSEI` is retained at `reports/evidence/daily_prediction_NIFTY50_2026-11-20.json`. Do not combine its metrics with the RELIANCE.NS result: they are different symbols and independently generated prediction runs. It also reports `WEAK_BELOW_BASELINE`.

## 2. V111 cost-aware three-class intraday experiment

The archived V111 experiment is a separate intraday research track using 5-minute Upstox V3 historical candles for NIFTY 50 (`NSE_INDEX|Nifty 50`). It was fetched at `2026-11-19T17:41:05Z`, with 1,439 candles and 1,373 engineered observations.

- Entry: next candle close.
- Exit: close four bars after the signal (three bars held).
- Round-trip cost proxy: 20 basis points (10 bps per side).
- Labels: DOWN below negative cost, NO_TRADE within the cost band, UP above positive cost.
- Evaluation: three expanding chronological folds, four-row boundary purge, no shuffling, and no test-based model/threshold selection.

### Three-class results

| Model | Mean accuracy | Mean balanced accuracy | Mean macro F1 |
|---|---:|---:|---:|
| Majority-class baseline | **88.50%** | 33.33% | 31.29% |
| Random Forest | **88.50%** | 33.33% | 31.29% |
| HistGradientBoosting | 88.21% | 35.14% | 34.55% |
| Logistic Regression | 87.19% | 35.11% | 33.77% |

Across the three test folds (687 test rows), class counts were DOWN 30 (4.37%), NO_TRADE 608 (88.50%), and UP 49 (7.13%). Therefore the high raw accuracy mainly reflects the dominant NO_TRADE class. The majority baseline predicts NO_TRADE for every row. HistGradientBoosting's 88.21% is below that 88.50% baseline. Balanced accuracy and macro F1 show that recognition of DOWN and UP remains weak.

The binary V111 benchmark is retained separately. Its candidate models did not demonstrate a convincing out-of-sample edge; the stored result reports zero executed research trades under the tested threshold policy. `trading_enabled` is false. V111 is an experimental diagnostic, not an order signal or proof of profitability.

The cost band is a simplified research proxy, not a full Indian broker fee model; it does not fully model all taxes, spread, slippage, market impact, or latency. Optional LSTM/GRU training is not claimed as completed by this result.

## 3. What is complete in this AI scope

- Daily prediction API and versioned RF + Extra Trees artifact registry are present.
- Chronological daily walk-forward evaluation, majority baseline, and conservative candidate gate are present.
- Intraday binary and V111 cost-aware three-class research paths are present.
- V111 result JSON and teacher-facing model guides are included.
- Research-only trading gate remains disabled; news is not silently injected into daily model probabilities.
- Current daily and intraday evidence is stored under `reports/evidence/` and the original V111 experiment JSON is retained at project root.

## 4. Verification performed for this package

The 129 backend tests were run successfully in groups in this environment:

| Test group | Result |
|---|---:|
| `tests/test_api.py` | 69 passed |
| `tests/test_engine.py tests/test_market_cache.py tests/test_news.py tests/test_upstox_stream.py` | 21 passed |
| `tests/test_analysis.py` | 9 passed |
| `tests/test_real_world.py tests/test_real_world_evaluation.py` | 28 passed |
| `tests/test_model_registry.py` | 2 passed |
| **Total** | **129 passed** |

A single all-tests invocation exceeded the environment time limit, so the complete set was verified in separate groups. The successful groups cover all 129 collected backend tests. Four SQLAlchemy `datetime.utcnow()` deprecation warnings appeared in the API group; they did not fail tests.

The focused V111 three-class tests also passed (3 passed), and the research-status/interval API checks passed (2 passed); these are included within the grouped totals above, not additional tests.

## 5. Final interpretation and limitations

BharatStock AI's implementation and research workflow are complete for this V111 AI scope, but predictive skill is **not established**. The daily directional model is below its majority baseline. V111's high raw three-class accuracy is explained by the dominant NO_TRADE class and does not mean 88% directional accuracy. No forced accuracy, artificial class balancing in the reported results, synthetic data, automatic candidate promotion, or guaranteed returns are claimed.

The archived metrics are reproducible evidence snapshots, not a promise that future API runs will produce identical numbers. Future market observations may change results. This project is an educational AI research application, not investment advice or an authorized live trading system.
