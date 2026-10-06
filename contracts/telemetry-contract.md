# Telemetry Contract v1

Logging: JSON lines when `NQTS_JSON_LOGS=true`, fields `ts`, `level`, `logger`, `msg`.
Metrics: counters `nqts_signals_total`, `nqts_orders_total`, `nqts_errors_total`;
gauges `nqts_open_positions`, `nqts_equity`; histograms `nqts_fill_latency_ms`.
Required event stream: intent → fill → risk check → portfolio allocation.
