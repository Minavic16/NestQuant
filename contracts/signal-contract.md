# Signal Contract v1

A strategy emits **signals**, never orders. NQTS translates validated signals
into intents through the execution adapter.

```json
{
  "strategy_id": "NQ-BREAKOUT-V1",
  "strategy_version": "2026-09-15",
  "pair": "EUR/USD",
  "direction": "long | short | flat",
  "timeframe": "4h",
  "confidence": 0.0,
  "intent": {"sl_in_pips": 0.0, "tp_in_pips": 0.0, "risk_pct": 0.0},
  "provenance": {"signal_hash": "...", "artifact_id": "...", "evaluated_at": "..."}
}
```

NQTS must not build trades from free-form strategy code output; it consumes
only this shape.
