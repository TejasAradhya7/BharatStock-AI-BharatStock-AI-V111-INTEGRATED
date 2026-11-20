# BharatStock AI V45 — Theme Implementation

## Included
- Added a persistent dark/light theme toggle in the dashboard header.
- Theme preference is saved under `bharatstock.theme` in browser local storage.
- Added light-theme styles for navigation, panels, charts surrounding UI, controls, watchlist, quote cards, alerts, tables, and analysis components.
- Toggle includes accessible label/title and switches between Sun and Moon icons.
- Existing real-provider data paths and backend routes were not replaced with demo data.

## Build verification
The frontend production build was not verified in this environment. `npm ci` cannot run because the source ZIP does not include a lockfile; `npm install` timed out in the available workspace. Please verify locally with:

```powershell
cd apps/web
npm install
npm run build
```

Then from the project root:

```powershell
docker compose up -d --build
```

Keep your existing `.env` and database data. This package excludes secrets and generated dependency/cache folders.
