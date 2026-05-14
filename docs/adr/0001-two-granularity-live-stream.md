# Live stream emits two granularities, not one

The dashboard's primary task is live monitoring of an active training Run. The frontend rebuild needed a price chart with per-Step trade markers (TradingView-feel), but the existing `training_update` event is per-Generation — too coarse for a chart, too summary-shaped to discard.

We considered replacing `training_update` with a single per-Step event and recomputing Sharpe / win-rate / progress on the frontend from raw Steps. We rejected it: those metrics are defined per-Generation in the trainer (Sharpe is the rolling average over an Episode evaluation, win-rate is a cumulative Trade ratio), so emitting them per-Step would either lie about what each measurement means or force the frontend to replicate trainer aggregation. We also rejected pure-frontend accumulation from `last_action` — Q5 already locked in backend-served per-Step series with `run_steps` persistence (see [ADR-0002](0002-persist-per-step-timeseries.md)).

Decision: backend emits **two** event types on the same WebSocket. `training_update` (per-Generation, pre-existing, unchanged shape) drives the KPI strip and Sharpe trajectory. `step_batch` (per-Step, new, batched at ~100ms) drives the live price chart and trade markers. Frontend consumes both. The contract is asymmetric on purpose — granularity matches what each surface actually displays.
