# Persist per-Step timeseries in `run_steps`

The frontend rebuild requires a price chart with per-Step granularity that survives page refresh and supports a future `/runs/:id` replay surface. Frontend-only accumulation was rejected because data evaporates on refresh and across browsers.

A single Run can produce ~25M Steps (`episode_length × total_episodes × generations`). We accept this volume on SQLite for now: a `run_steps(run_id, gen, episode, step, ts, price, action, position, balance)` table indexed on `(run_id, ts)`, with retention pruning aligned to the existing 90-day policy in `RunLifecycleModule.start`. Decimation (e.g. LTTB) for historic queries is deferred until a real read pattern shows the unindexed scan is slow — premature optimisation today.

Decision: persist Steps row-per-Step, not aggregated. Live writes are batched by the same 100ms batcher that drives `step_batch` so the trainer hot-loop stays decoupled from the database. If row volume becomes a problem, two reversible levers exist before the schema needs to change: pre-decimate on insert (sample 1-in-N) or move historic data to Parquet (already a project dependency). The `run_steps` table itself is the load-bearing decision — once a Run's data is there, downstream queries depend on its shape.
