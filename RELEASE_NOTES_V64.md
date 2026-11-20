# BharatStock AI V64 — Chart Response Contract Fix

## Why this revision exists
The V63 screenshot still showed zero valid OHLC candles while a provider timestamp was present. V63's source had weekly/monthly aggregation, but the browser outcome proved that alone did not fix the actual response-to-chart path.

## Changes
- `/api/chart/{symbol}` now constructs each response record explicitly with `time`, numeric `Open`, `High`, `Low`, `Close`, and nullable `Volume` from provider rows.
- Validates OHLC ordering before returning bars; invalid/empty results produce a clear API error instead of a successful response containing unusable bars.
- Updates legacy source-check assertions to match the actual timestamp/volume normalization implementation rather than outdated string patterns.
- Adds V64 chart contract source checks.

## Limits
This is a source-level correction. Live Yahoo Finance access and browser rendering have not been exercised in this environment; frontend build status is unverified. Upstox HTTP 403 is a separate authentication/permission issue. No synthetic candles are created.
