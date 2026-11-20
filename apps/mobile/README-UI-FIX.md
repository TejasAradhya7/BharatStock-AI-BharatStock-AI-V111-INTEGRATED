# BharatStock AI Mobile UI Fix

This package updates the shared API screen so backend JSON is displayed as readable metric cards, detail rows, nested sections, and list cards instead of a large raw JSON block. CSV responses receive a compact table preview.

## Run

1. Keep the FastAPI backend running.
2. Check `mobile/.env`. For Expo Go on a physical phone, `EXPO_PUBLIC_API_URL` must use the computer's reachable LAN IPv4 address, for example `http://192.168.1.10:8000` (use your actual address).
3. From the `mobile` directory, run:

   ```powershell
   npm install
   npx expo start --clear
   ```

4. Open the project in Expo Go and refresh Analysis, Risk, Backtest, and Research.

## Notes

- The UI uses existing API responses; it does not change or improve model accuracy.
- HTTP 200 only indicates that the request succeeded. Research responses can still report insufficient data.
- Research sentiment is currently a text-sentiment endpoint test, not a live market sentiment calculation.
- Keep API tokens and other secrets out of `.env` values prefixed with `EXPO_PUBLIC_`; Expo exposes those values to the client.


## Follow-up readability improvements

- Long API arrays now show the first three records initially with a Show all / Show less control.
- Existing metric cards and structured detail rendering are preserved.
- The uploaded `.env` file is intentionally excluded from the distributable ZIP to avoid packaging API credentials. Copy your local environment values into `.env` after extraction; `.env.example` is included as a reference.
