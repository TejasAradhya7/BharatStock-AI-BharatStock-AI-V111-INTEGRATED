# BharatStock AI V104 — Project Finalization and Honest Completion Report

**Project:** BharatStock AI  
**Release:** V104 Finalized Research/Submission Pack  
**Date:** 19 November 2026

## 1. Project decision

The project will **accept the current measured model performance** rather than force a target accuracy. The current prediction pipeline and research results are retained honestly. No claim of 60% accuracy, guaranteed profit, or production trading readiness is made.

The live API model remains the established Random Forest + Extra Trees soft-voting ensemble. The V103 NIFTY-aware HistGradientBoosting model is a research candidate only and is not automatically promoted.

## 2. Current V103 evidence supplied by the project owner

The supplied V103 run covers 13 NSE equities plus NIFTY 50, from 1 December 2020 through 18 November 2026, using five expanding chronological global-date folds with a one-date purge.

| Feature set / model | Mean accuracy | Balanced accuracy | AUC |
|---|---:|---:|---:|
| Stock-only Extra Trees | 50.80% | 51.06% | 0.5098 |
| Stock-only Random Forest | 50.33% | 50.53% | 0.5076 |
| Stock-only HistGradientBoosting | 50.28% | 50.49% | 0.5017 |
| Stock + NIFTY Extra Trees | 51.63% | 51.58% | 0.5185 |
| Stock + NIFTY HistGradientBoosting | **51.68%** | 51.55% | **0.5205** |
| Stock + NIFTY Random Forest | 50.67% | 50.60% | 0.5125 |

These are modest directional classification results. AUC values near 0.5 indicate weak ranking ability. They do not establish a durable predictive edge.

## 3. Cost-aware diagnostic supplied

The V103 diagnostic used a fixed probability threshold of 0.55, a 0.10% assumed round-trip cost, and next-session open-to-close returns. Results:

| Model | Signals | Coverage | Win rate | Mean net trade return | Compounded diagnostic return |
|---|---:|---:|---:|---:|---:|
| Extra Trees | 158 | 1.64% | 46.84% | +0.099% | -2.85% |
| Random Forest | 433 | 4.50% | 46.88% | +0.036% | -7.10% |
| HistGradientBoosting | 1,669 | 17.35% | 45.00% | -0.070% | -37.17% |
| Logistic Regression | 572 | 5.95% | 44.58% | -0.149% | -42.81% |
| XGBoost | 2,045 | 21.26% | 45.53% | -0.079% | -23.31% |

This is an illustrative diagnostic, not a brokerage-grade backtest. Its execution assumptions, portfolio sizing, capital allocation, overlapping exposure and actual charges need further review. It must not be presented as proof of profitability.

## 4. Final model policy

- Keep the existing API Random Forest + Extra Trees ensemble as the live research baseline.
- Keep stock + NIFTY HistGradientBoosting as the strongest V103 classification research candidate by mean accuracy/AUC.
- Do not automatically deploy the V103 candidate: its cost-aware diagnostic is materially negative.
- Show model scores as research scores, not calibrated probability of profit.
- Preserve no-signal / risk-warning behavior where applicable.
- No broker order placement or real-money execution is enabled by this research pack.

## 5. Included project components

The base project contains:
- React + TypeScript web dashboard
- Expo / React Native mobile client
- FastAPI backend
- PostgreSQL and Docker Compose configuration
- Upstox quote / market-data integration code
- Technical indicators, sentiment endpoint, prediction and research modules
- Backend tests and existing release/audit notes
- V102 and V103 research notebooks

This V104 pack adds:
- This project completion and model governance report
- Teacher demonstration guide
- V103 model summary, fold metrics, stock/regime results, cost diagnostic and validation report
- V103 combined NSE + NIFTY daily dataset used for the research run

## 6. Verification status

Previously supplied V101 audit reported 121 backend tests passing, Python syntax checks passing, and UI regression checks passing. However, those do not prove full-stack production readiness.

A fresh backend test attempt during V104 packaging did not finish within the five-minute execution limit; it was stopped while tests were still running. Therefore this pack does **not** claim a fresh complete test pass.

Still requiring verification in the user's target environment:
- Complete backend pytest suite to completion
- Web production build and browser end-to-end tests
- Expo mobile build on target Android/iOS environment
- Docker Compose + PostgreSQL runtime and persistent volume behavior
- Real Upstox authentication, quote freshness and WebSocket behavior with the user's own valid token
- Deployment CORS, secrets, logging, backup and recovery checks

## 7. Honest completion statement

BharatStock AI is a substantial implemented AIML research application with web, mobile, backend, data-provider and model-research components. Its current measured directional model performance is around 51–52% on the supplied V103 walk-forward comparison. The project accepts this result rather than manipulating accuracy.

**Academic/research status:** suitable for a carefully qualified demonstration of a multi-stock Indian equity analytics and ML research system, subject to the remaining environment-specific build/runtime checks.

**Production trading status:** not certified; no profitability claim.
