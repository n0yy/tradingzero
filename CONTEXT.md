# TradingZero — Domain Glossary

This file captures the domain language used across TradingZero. Skills consume this when designing, naming, or discussing concepts. If a term is missing, that's a signal — either we're inventing language the project doesn't use, or there's a real gap to fill.

## Concepts

### Run

A single end-to-end training session, started by `POST /runs/start`. Owns its own config revision, generations, episodes, and steps. Has a lifecycle state: `idle → running → (stopping →) done | error`. Identified by `run_id` (timestamp string).

### Generation

One training generation inside a Run. PPO trains, then evaluates; if Sharpe beats the previous best by `promote_threshold`, the agent is promoted and saved as a checkpoint. Multiple generations per Run.

### Episode

One simulated trading session inside a Generation. Configurable length (`episode_length`, default 500 steps). The agent starts with `initial_balance`, observes 60 candles × 7 channels, makes step-by-step decisions until the episode ends. Many episodes per Generation.

### Step

One discrete agent decision inside an Episode. At each step, the agent observes the current window, picks `(direction, size)` from `MultiDiscrete([3, 4])`, and the environment advances one candle. A Step is the finest-grained unit of training data — a Run can produce ~25M of them.

### Action

One Step's decision. Components:
- **Direction**: HOLD | BUY | SELL
- **Size**: 25% | 50% | 75% | 100% of available capital
- **Position before/after**: fraction of capital invested, in [0, 1]

### Requested Action

The raw Action proposed by the policy for a Step, before environment constraints such as an already-full or already-empty position are applied.

### Executed Trade

The actual position delta applied by the environment on a Step; this is the source of truth for cumulative BUY/SELL and overtrading analysis.

### Transaction Count

The number of Steps that produced a non-zero Executed Trade; one Step contributes at most one BUY or one SELL transaction regardless of size delta.

### Transaction Outcome

The per-Step portfolio outcome used by the live dashboard: BUY, SELL, or NO TRANSACTION.

### Trade Win Rate

The cumulative ratio of winning realized exits to all realized exits in the current Run. Computed from `realized_pnl` on SELL-side **Executed Trade** records; BUY trades do not count toward the denominator because they do not realize PnL yet.

## Relationships

- A **Requested Action** may or may not produce an **Executed Trade**
- **Transaction Count** is derived from **Executed Trade**, not from **Requested Action**

### Last Transaction

The most recent Executed Trade emitted on the live training stream. Surfaced in the dashboard for at-a-glance visibility because it reflects what actually changed in the portfolio.

### Live Stream

The WebSocket connection from frontend to `/ws/runs/stream`. Pushes `training_update` events while a Run is active. Dashboard shows `connected | disconnected` for this stream — distinct from Run state.

## Visual concepts (dashboard)

### Live View

The dashboard's primary screen. Shows the active Run as it trains. Hero element is the price chart with overlaid trade markers. Live View is always-on — when no Run is active, it shows an idle/connecting affordance, not blank.

### Rolling window (chart)

The Live View's price chart renders only the most recent N Steps (default 500). Older Steps scroll off the left edge as new ones arrive. They remain in the database, queryable via history endpoints, but are not in the live viewport. This is "TV screen" semantics — focused on the present, not browsable in-place.

The price line is continuous across all Steps. Trade markers appear only for Steps that produced an **Executed Trade**.

### Step batch

The unit of WebSocket push for live updates. Backend buffers Steps as the trainer emits them, then flushes a batch every ~100ms (~10 fps). One `step_batch` event carries an array of Step records. Per-step push would saturate the browser; per-episode push would feel choppy. 100ms batches are the floor where smoothness matches what the eye perceives as continuous motion.

### Training update

The per-Generation summary event on the live stream (`training_update`). Carries Sharpe, best-Sharpe, trade-win-rate, transaction distribution, last transaction, and progress. Pre-existing event, retained alongside Step batch — they serve different views: KPI strip consumes `training_update` (per-gen) plus live Step deltas, while the price chart consumes `step_batch` (per-step). Aggregating Sharpe from raw Steps would be noisy; emitting Steps as if they were Generations would lie about what each measurement means.

## Surfaces (dashboard routes)

### Live View — `/`

Default route. Hero is the price chart with overlaid trade markers. KPI strip on top (Sharpe, best Sharpe, balance, PnL, trade win rate, progress). Below the chart: three compact panels — Last Transaction, Run Controls, Transaction Distribution. Side nav on the left for secondary surfaces.

Live View has three idle states, each with its own affordance:
- **Disconnected** (Live Stream not connected): warning banner + retry, chart skeleton.
- **Idle** (no Run active): prominent Start CTA, chart skeleton.
- **Waiting** (Run active, no Step batch yet): spinner + "waiting for first step batch", KPIs show `--`.

Never a blank chart — a blank chart hides whether the system is healthy.

### Runs — `/runs`, `/runs/:id`

List of past Runs with state and timing. Clicking a Run opens a read-only replay (Phase 3 scope). Live Run is just the topmost item.

### Config — `/config`

Full-page form. Four accordion groups matching the backend `SafeConfigPayload`: Data, Env, Agent, Self-play. Each field has inline help (typical range, unit, training effect). Validated client-side with zod + react-hook-form. Save Revision button is sticky and disabled when pristine or invalid.

A Sheet (slide-over) is also accessible from the Live View topbar for quick edits to the 3-4 most-tweaked fields when a Run is idle.

### Errors — `/errors`

Global error explorer (cross-Run). Per-Run errors still accessible from a Run detail page, but a global view exists for triage.
