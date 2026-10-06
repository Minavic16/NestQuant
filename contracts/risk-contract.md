# Risk Contract v1

Breaker states: `OK`, `PAUSE` (block new entries, let trades run),
`HARD_STOP` (flatten + halt).

Persistence is JSON with atomic write (temp + rename). The risk engine owns:
- max drawdown / dd pacing
- slippage guards
- floating-loss kill
- per-account and per-currency limits (multi-account)
