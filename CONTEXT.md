# TradingZero — Domain Glossary

This file captures the domain language used across TradingZero. Skills consume this when designing, naming, or discussing concepts. If a term is missing, that's a signal — either we're inventing language the project doesn't use, or there's a real gap to fill.

## Concepts

### Run

A single end-to-end training session, started by `POST /runs/start`. Owns its own config revision, generations, episodes, and steps. Has a lifecycle state: `idle → running → (stopping →) done | error`. Identified by `run_id` (timestamp string).

### Training Slice

The subset of historical candles a Run is allowed to learn from. Metrics observed on this slice are in-sample and are useful for training diagnostics, but they are not sufficient to justify checkpoint promotion on their own.

### Evaluation Slice

A fixed out-of-sample chronological holdout of historical candles reserved for deterministic evaluation during a Run. It is taken from a different time range than the Training Slice, not from the same candles with a different seed. For Milestone 1, the Evaluation Slice is one contiguous time block. It remains unchanged for the full lifetime of a Run so Generation-to-Generation comparisons stay meaningful, and it is read-only for evaluation rather than a source of learning or tuning. `best_sharpe` and checkpoint promotion are sourced from this slice, not from Training Slice episodes.

### Evaluation Anchor

A fixed start point inside the Evaluation Slice from which a deterministic evaluation episode begins. The set of Evaluation Anchors for a Run is chosen once, spread evenly across the full Evaluation Slice, and then reused unchanged for every Generation.

### Evaluation Spec

The persisted definition of the evaluation setup for a Run. It records which Evaluation Slice was used, which Evaluation Anchors were chosen, the episode length, and the evaluation seed needed to replay the same Evaluation Pass later.

### Training Seed

The persisted random seed used for learning during a Run. It helps explain why one Run may learn differently from another and makes training behavior easier to compare and audit.

### Evaluation Seed

The persisted random seed used for deterministic evaluation during a Run. It is part of the Evaluation Spec and helps ensure the same Evaluation Pass can be replayed consistently.

### Generation

One training generation inside a Run. PPO trains, then evaluates; if its Promotion Gate is satisfied and its Evaluation Sharpe beats the previous best by `promote_threshold`, the agent is promoted and saved as a checkpoint. Multiple generations per Run.

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


### Trade Cooldown

A mandatory minimum number of Steps that must elapse after any Executed Trade (BUY or SELL) before the agent is allowed to trade again. Enforced via action masking in the environment. Default: 10 Steps (equivalent to 2.5 hours at 15m timeframe). Prevents overtrading without penalising individually profitable trades.

### Action Mask

A per-Step boolean vector over the full action space that marks which actions are valid given the current environment state. Applied via `MaskablePPO` (sb3-contrib) so the policy never receives gradients from invalid actions. Invalid conditions: BUY when position = 1.0, SELL when position = 0.0, any trade during Trade Cooldown.

### Baseline Benchmark

A set of reference strategies evaluated once per Run on the same Evaluation Slice and Evaluation Anchors as the agent. Two baselines are defined: **Random** (action sampled uniformly from the action space each Step) and **Buy-and-Hold** (full BUY at episode start, held until truncation). Baseline Sharpe values are stored in the Evaluation Spec and used as a lower bound for agent quality assessment.

### Step Return Reward

The primary reward signal. Defined as `(balance_after - balance_before) / balance_before` per Step. Direct, non-lagging, and proportional to actual profit or loss each candle.

### Realized PnL Bonus

A secondary reward term applied only when a SELL Executed Trade closes or reduces a position. Defined as `clip(realized_pnl / balance_before * 3.0, -0.5, 0.5)`. Addresses the credit assignment problem — without it, the profit or loss from a trade is spread across many Steps during the hold period, making it hard for the policy to associate the reward with the BUY or SELL decision that caused it. Profit exits receive a positive bonus; loss exits receive a penalty. The multiplier and clip bounds are intentionally conservative to avoid dominating the Step Return signal.

## Relationships

- A **Requested Action** may or may not produce an **Executed Trade**
- **Transaction Count** is derived from **Executed Trade**, not from **Requested Action**
- A **Run** may consume separate **Training Slice** and **Evaluation Slice**
- A **Run** should persist its **Evaluation Spec** so the same Evaluation Pass can be audited and replayed later
- A **Run** should persist both its **Training Seed** and **Evaluation Seed**
- An **Evaluation Pass** reuses the same **Evaluation Anchors** for every **Generation** in a **Run**
- Each **Generation** should persist an **Evaluation Record**
- **Best Evaluation Sharpe** is derived from the **Evaluation Slice**, not from the **Training Slice**

### Last Transaction

The most recent Executed Trade emitted on the live training stream. Surfaced in the dashboard for at-a-glance visibility because it reflects what actually changed in the portfolio.

### Live Stream

The WebSocket connection from frontend to `/ws/runs/stream`. Pushes `training_update` events while a Run is active. Dashboard shows `connected | disconnected` for this stream — distinct from Run state.

## Visual concepts (dashboard)

### Live View

The dashboard's primary screen. Shows the active Run as it trains. Hero element is the price chart with overlaid trade markers. Live View is always-on — when no Run is active, it shows an idle/connecting affordance, not blank.

For Milestone 1, Live View stays training-dominant. Roughly 70% of the surface is for live monitoring and 30% is for a dedicated Evaluation section that explains checkpoint trustworthiness without turning the page into a Battle screen.

The main Training hero and the Evaluation Section sit side-by-side rather than top-and-bottom. The dashboard should also feel compact: smaller padding, less dead center whitespace, and fuller use of the available viewport width.

Within that side-by-side layout, the live chart remains on the left and the Evaluation Section sits on the right.

On desktop, the target width split is roughly 70 / 30 between the chart and the Evaluation Section.

On narrower screens, the layout stacks vertically with the live chart first and the Evaluation Section immediately below it.

Existing live-monitoring panels such as Transaction Distribution, Last Transaction, and Run Status remain as a separate row below the hero area rather than being absorbed into the Evaluation Section.

In the compact Live View layout, the lower live-monitoring row is ordered as Run Controls/Run Status first, Last Transaction second, and Transaction Distribution third.

### Rolling window (chart)

The Live View's price chart renders only the most recent N Steps (default 500). Older Steps scroll off the left edge as new ones arrive. They remain in the database, queryable via history endpoints, but are not in the live viewport. This is "TV screen" semantics — focused on the present, not browsable in-place.

The price line is continuous across all Steps. Trade markers appear only for Steps that produced an **Executed Trade**.

### Step batch

The unit of WebSocket push for live updates. Backend buffers Steps as the trainer emits them, then flushes a batch every ~100ms (~10 fps). One `step_batch` event carries an array of Step records. Per-step push would saturate the browser; per-episode push would feel choppy. 100ms batches are the floor where smoothness matches what the eye perceives as continuous motion.

### Training update

The per-Generation summary event on the live stream (`training_update`). Carries Training metrics and Evaluation metrics as distinct values, alongside trade-win-rate, transaction distribution, last transaction, and progress. It is retained alongside Step batch — they serve different views: KPI strip consumes `training_update` (per-gen) plus live Step deltas, while the price chart consumes `step_batch` (per-step). Aggregating Sharpe from raw Steps would be noisy; emitting Steps as if they were Generations would lie about what each measurement means.

### Evaluation Pass

The deterministic per-Generation checkpoint test run over the Evaluation Slice. It is composed of multiple fixed-anchor episodes and produces the metrics used for `best_sharpe` and checkpoint promotion.

### Evaluation Record

The persisted per-Generation result of an Evaluation Pass. It stores the Generation's Evaluation Sharpe, activity counts used by the Promotion Gate, the promotion decision, the human-readable reasons behind that decision, and per-anchor evaluation detail rather than only a single merged score.

### Evaluation Section

The dedicated part of Live View that summarizes the latest in-Run Evaluation Pass. It is separate from the Battle route: Evaluation explains whether the current Generation is trustworthy enough to promote, while Battle runs the promoted `best.zip` as a standalone deterministic inference pass. The section is decision-first: the primary message is whether the current Generation was **Promoted** or **Not promoted**, followed by a one-sentence summary and a checklist of Promotion Gate checks that explain why. Each checklist row should show the actual metric value against the comparison target or threshold, not only a pass/fail label. The always-visible metrics are **Evaluation Sharpe**, **Best Evaluation Sharpe**, **Executed Trade count**, and **SELL realized exits**. Per-anchor detail is available as expandable drill-down content rather than always-open content.

In the Live View UI, this section is titled **Promotion Check** to make its purpose explicit.

Within Promotion Check, the current Generation's evaluation outcome is visually primary. **Best Evaluation Sharpe** remains visible as comparison context, but not as the main headline figure.

When expanded, per-anchor detail is shown as a compact comparison table rather than a stack of cards, because the primary job of that drill-down is cross-anchor comparison.

The minimum per-anchor columns are **Anchor**, **Evaluation Sharpe**, **Executed Trades**, **SELL realized exits**, and **Result**.

The **Anchor** column should identify each anchor with a short stable label plus its start time, so it is both easy to reference and easy to place within the Evaluation Slice.

In the per-anchor table, **Result** is `Pass` or `Fail` for that anchor. This is intentionally different from the section-level decision of `Promoted` or `Not promoted`.

Per-anchor failure reasons are secondary detail, not primary table columns. The table stays compact for comparison, while row-level explanations are revealed only on demand.

The Evaluation Section remains visible even before the first Evaluation Pass finishes. In that state, it should show an explicit waiting or empty message rather than appearing late or leaving a blank gap in Live View.

Copy in the Evaluation Section should be friendly but precise: easy to understand quickly, while still using the correct domain terms such as Evaluation Pass and Promotion.

The Live View is the primary home of evaluation detail during an active Run. Secondary surfaces such as Runs/history may show compact evaluation summaries later, but they are not the main place for in-Run promotion diagnosis.

Training Sharpe may appear inside the Evaluation Section as secondary context for comparing in-sample versus out-of-sample behavior, but it is not a headline metric there.

The Live View Evaluation Section focuses on the latest Generation only. Longer evaluation history belongs to secondary surfaces rather than the compact right-side inspector.

### Evaluation Sharpe

The average Sharpe across all episodes in an Evaluation Pass. It is the score compared Generation-to-Generation and is the source of `best_sharpe`.

### Best Evaluation Sharpe

The highest Evaluation Sharpe achieved so far within a Run. This is the human-facing meaning of `best_sharpe` and should be labeled explicitly as an Evaluation metric in logs and UI so it is not confused with Training Sharpe.

### Training Sharpe

The in-sample Sharpe observed on the Training Slice. It is useful for diagnosing learning progress, but it is not the score used for checkpoint promotion.

### Promotion Gate

The full set of conditions a Generation must satisfy before its checkpoint can replace `best.zip`. For Milestone 1, checkpoint promotion is intentionally simple: it is driven by **Evaluation Sharpe** plus minimum evidence that the policy actually traded enough to make the score meaningful. The first two activity checks are minimum **Executed Trade** count and minimum SELL-side realized exits within the Evaluation Pass, and both are defined as fixed numeric thresholds rather than percentages. Initial thresholds are intentionally loose enough to catch obviously untrustworthy results without blocking nearly every Generation. Each Generation should also surface a human-readable pass/fail reason for every Promotion Gate check in logs and UI. Other metrics such as PnL remain visible for interpretation, but they are not promotion conditions in Milestone 1.

## Surfaces (dashboard routes)

### Live View — `/`

Default route. Hero is the price chart with overlaid trade markers. KPI strip on top is kept compact and live-focused: balance, PnL, trade win rate, and progress. Evaluation-specific Sharpe metrics live in the dedicated Evaluation Section instead of crowding the top strip. Below the hero area: three compact panels — Last Transaction, Run Controls, Transaction Distribution. Low-priority analytics such as Profit vs Loss Steps do not remain as primary Live View content in the compact layout. Side nav on the left for secondary surfaces.

Live View has three idle states, each with its own affordance:
- **Disconnected** (Live Stream not connected): warning banner + retry, chart skeleton.
- **Idle** (no Run active): prominent Start CTA, chart skeleton.
- **Waiting** (Run active, no Step batch yet): spinner + "waiting for first step batch", KPIs show `--`.

Never a blank chart — a blank chart hides whether the system is healthy.

### Runs — `/runs`, `/runs/:id`

List of past Runs with state and timing. Clicking a Run opens a read-only replay (Phase 3 scope). Live Run is just the topmost item. Runs/history may later surface compact evaluation summaries for audit, but not the full Live View Evaluation Section.

### Config — `/config`

Full-page form. Four accordion groups matching the backend `SafeConfigPayload`: Data, Env, Agent, Self-play. Each field has inline help (typical range, unit, training effect). Validated client-side with zod + react-hook-form. Save Revision button is sticky and disabled when pristine or invalid.

A Sheet (slide-over) is also accessible from the Live View topbar for quick edits to the 3-4 most-tweaked fields when a Run is idle.

### Errors — `/errors`

Global error explorer (cross-Run). Per-Run errors still accessible from a Run detail page, but a global view exists for triage.

## Engineering context

This section is implementation-facing context for contributors. It complements the domain glossary above and is intentionally stack-oriented.

### Web app stack — `apps/web`

- React 19 + TypeScript
- Vite 8
- React Router 7
- TanStack Query 5
- Tailwind CSS v4 via `@tailwindcss/vite`
- shadcn/ui (`new-york` style, `neutral` base color, Lucide icons)
- Zustand for lightweight UI state
- Vitest + Testing Library for component/unit tests
- Playwright for E2E smoke/debug coverage

Frontend styling direction for the dashboard is a full rewrite to Tailwind CSS v4 rather than a long-lived mix of legacy App.css layout rules and new utility classes.

The dashboard's structural layout is preserved during that rewrite, while theme and color treatment may be improved as long as UI/UX remains clear and high-signal. Reusable interface pieces should prefer shadcn/ui building blocks such as Card, Tabs, and collapsible navigation patterns instead of bespoke styling where a standard composable primitive fits.

The primary dashboard navigation should use a shadcn-style collapsible sidebar rather than a permanently expanded static rail.

On desktop, that sidebar defaults to expanded so the available surfaces remain easy to discover before the user chooses to collapse it for focus.

Responsive sidebar behavior is intentionally deferred for now. Mobile and narrow-screen navigation details are not part of the current dashboard decision set.

The desktop sidebar navigation remains a flat list for now. The current surface count is small enough that category grouping would add noise more than clarity.

When the sidebar becomes the primary navigation, duplicate topbar mode tabs such as Training/Battle should be removed. The header should not repeat navigation that already exists in the sidebar.

Secondary utilities should move out of the topbar and into the sidebar footer. The first planned footer utilities are the Time mode toggle and a Dark/Light theme toggle placeholder, even if theme switching is not implemented yet.

Those sidebar footer utilities are shown as separate rows rather than cramped side-by-side buttons.

The topbar stays minimal: page title first, status badge second, and only very short supporting copy when truly needed. The status badge should include a small pulse dot so live state is legible at a glance.

### Backend stack

- FastAPI + Uvicorn
- Pydantic 2
- SQLAlchemy 2 + Alembic
- WebSocket live stream for Run updates
- SQLite persistence for local runtime data

### Training stack

- PyTorch
- Stable-Baselines3 PPO
- Gymnasium environment
- Pandas + NumPy for data shaping
- CCXT for exchange candle ingestion

### Terminal app stack — `apps/tui`

- Textual + Rich
