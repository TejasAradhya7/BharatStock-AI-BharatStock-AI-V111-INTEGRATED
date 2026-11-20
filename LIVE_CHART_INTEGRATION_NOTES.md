# Live chart integration notes

## Changes
- Added a separate live quote-observation chart to the existing web dashboard.
- Historical OHLC chart remains unchanged and is still the default view.
- Live chart accepts observations only while the WebSocket is connected, the feed reports `live`, and the latest quote is no more than 30 seconds old.
- REST snapshot fallback data is not presented as live ticks.
- The live chart is explicitly labelled as quote observations, not OHLC candles or an exchange trade tape.
- Switching symbols resets the live observation history.

## Build and validation
- Source changes were applied to `apps/web/src/App.tsx` and `apps/web/src/style.css`.
- A frontend production build could not be completed in this packaging environment because `npm ci` did not finish before the execution timeout. Run `npm ci` and `npm run build` in `apps/web` on the development machine before deployment.
- Backend source, database schema, model artifacts and Upstox configuration were not intentionally changed by this chart integration.

## Safety and data notes
- No `.env` secret file is included. Configure credentials locally using `.env` based on `.env.example`.
- Keep the existing PostgreSQL and model-artifact Docker volumes when upgrading. Do not use `docker compose down -v`.
- The live chart requires an active market feed; outside exchange hours it may correctly show no fresh ticks.
