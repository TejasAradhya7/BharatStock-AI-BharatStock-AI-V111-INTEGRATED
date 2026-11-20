# V104.1 Web TypeScript Build Fix

This is an additive source correction to V104.

## Fixed issue
`apps/web/src/App.tsx` used `item.data_quality` and `item.data_quality_note` in the trade research journal, but the frontend `TradeIdea` type did not declare these optional fields. The backend API already returns these fields for index trade idea records.

## Change
Added:
- `data_quality?: string | null`
- `data_quality_note?: string | null`

No runtime business logic, API response, model, database, or credentials were changed.

## Run
Extract this ZIP, replace the previous extracted project folder, then run:
`docker compose up -d --build`

This patch addresses the TypeScript errors shown in the user's Docker build log. It does not certify that all subsequent build/runtime checks will pass; report any next error output for the next fix.
