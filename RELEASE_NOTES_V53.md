# BharatStock AI V53 — Live Freshness and Production Gate

## Changes
- Live quote freshness now updates every five seconds without needing a new quote packet.
- The live status badge stops showing a healthy/green state when the most recent quote is older than 30 seconds or no timestamp is available.
- The dashboard explicitly distinguishes stale quotes from quotes waiting for the first timestamp.
- Retains the V50/V51/V52 screenshot and messaging fixes present in the base source.

## Scope and limitations
- Price alerts remain browser-local and only operate while the dashboard is open; this is disclosed in the UI. Server-side alert delivery is not implemented by this release.
- The browser freshness display is not proof that Upstox reconnect/token recovery works; that still needs live integration tests.
- Production build and end-to-end browser testing must pass before calling this release production-ready.
