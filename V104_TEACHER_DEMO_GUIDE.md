# BharatStock AI — Teacher Demonstration Guide

## 1. Short introduction

“BharatStock AI is an Indian stock-market analytics and machine-learning research application. It combines historical OHLCV data, technical indicators, NIFTY 50 market context, model comparisons, sentiment analysis and risk/paper-trading tools. It has a React web interface, an Expo mobile client and a FastAPI backend with PostgreSQL support.”

## 2. Where is the AI prediction model?

“The live API currently uses a Random Forest and Extra Trees soft-voting ensemble for next-session direction research. I also developed a separate research benchmark that compares Logistic Regression, Random Forest, Extra Trees, HistGradientBoosting and XGBoost, with and without NIFTY 50 context.”

## 3. What accuracy did you achieve?

“In my latest five-fold chronological V103 experiment, the best mean accuracy was 51.68% for HistGradientBoosting with NIFTY 50 context. Its mean AUC was about 0.5205. This is a modest result and I report it honestly rather than claiming 60%.”

## 4. Why is accuracy not high?

“Daily stock direction is noisy and affected by many factors. The model has limited historical features and no complete point-in-time historical news archive. Market behavior changes over time, so performance varies between test periods and stocks.”

## 5. Does the model make money?

“No profitability claim is made. The illustrative cost-aware paper-trading diagnostic was negative on compounded return for all tested candidates. It is a research system, not a live trading recommendation engine.”

## 6. Why include NIFTY 50?

“NIFTY 50 gives broad market context. The experiment compares stock-only indicators against the same stock indicators plus NIFTY returns and volatility. In the V103 experiment, the market-context models had modestly better mean classification metrics.”

## 7. What is the research contribution?

“The project evaluates multi-stock Indian equity direction prediction using chronological validation, compares classical machine-learning models, tests NIFTY market context, examines volatility regimes and reports a cost-aware diagnostic rather than relying on accuracy alone.”

## 8. What are the limitations?

- The measured predictive edge is weak.
- The NIFTY-aware model is not promoted into the live API.
- LSTM/GRU comparison remains pending.
- Sentiment is not joined to a complete historical point-in-time news dataset.
- Web/mobile builds, full E2E, Docker/PostgreSQL and live Upstox integration still need verification in the target environment.

## 9. Suggested live demo order

1. Show the dashboard and supported market symbols.
2. Show technical indicators and market data source status.
3. Show the AI prediction panel and explain that its score is not a probability of profit.
4. Open Research Lab and explain chronological validation.
5. Show V103 model summary and compare stock-only vs stock + NIFTY.
6. Show regime results and the cost-aware diagnostic.
7. Show the limitations and future work honestly.

## 10. One-sentence conclusion

“BharatStock AI demonstrates an end-to-end Indian equity analytics and machine-learning research workflow, while transparently reporting the current model's modest predictive performance and its limitations.”
