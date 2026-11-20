# V75 — Confidence-gated demo trading

- Added a paper-trading simulator to the AI predictions workspace.
- Demo entries are available only when a valid UP/DOWN model direction exists and the model confidence score is at least 60%.
- Users choose a whole-share quantity and open a virtual long (UP) or short (DOWN) position at an available live quote, falling back to the latest historical close only when live quote data is unavailable.
- Open positions show mark-to-market simulated P/L; closing records an exit price and final simulated P/L.
- Paper trade history persists in browser local storage and can be cleared.
- No broker connection, real orders, or real money handling was added.
- The 60% threshold refers to the model's confidence score, not a calibrated probability of success or profit. Headline sentiment alone does not trigger a trade.
