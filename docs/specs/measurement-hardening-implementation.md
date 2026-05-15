# Measurement Hardening Implementation Spec

This document turns [ADR-0004](../adr/0004-measurement-hardening-evaluation-model.md) into an implementation checklist for Milestone 1.

## Goal

Make checkpoint promotion trustworthy enough that `best.zip` means "best on a fixed out-of-sample test", not "best on the same data the agent just learned from".

## Scope

Milestone 1 includes:

- separate **Training Slice** and **Evaluation Slice**
- one fixed chronological Evaluation Slice per Run
- deterministic **Evaluation Pass** using evenly spaced fixed **Evaluation Anchors**
- separate `Training Sharpe` and `Evaluation Sharpe`
- checkpoint promotion driven by `Evaluation Sharpe` plus a simple `Promotion Gate`
- persisted `Evaluation Spec`, `Training Seed`, `Evaluation Seed`, and per-Generation `Evaluation Record`
- human-readable promotion pass/fail reasons in logs and UI

Milestone 1 does not include:

- multi-block or regime-aware evaluation holdouts
- promotion gates based on PnL, drawdown, or win rate
- dynamic or per-Generation-changing evaluation slices
- reworking the live step stream contract beyond what is needed to expose the new metrics

## Non-negotiable rules

- Training data and evaluation data must not come from the same candle range in a Run.
- The Evaluation Slice must be chosen once per Run and remain fixed for the whole Run.
- Evaluation must be replayable from persisted metadata.
- `best_sharpe` is a human-facing `Best Evaluation Sharpe`, not a training metric.
- Promotion must fail loudly with explicit reasons when any gate check is not satisfied.

## Implementation checklist

### 1. Data split and runtime wiring

- Add a runtime step that splits fetched candles into `Training Slice` and `Evaluation Slice`.
- Use a chronological split, not random sampling.
- Keep the Evaluation Slice as one contiguous holdout block for the full Run.
- Persist enough slice metadata to identify the exact candle range used by each slice.
- Pass separate training/evaluation data into trainer/runtime instead of one shared dataset.

### 2. Evaluation spec generation

- Create an `Evaluation Spec` once when the Run starts.
- Persist:
  - Evaluation Slice identity or boundaries
  - Evaluation Anchors
  - evaluation episode length
  - evaluation seed
- Generate anchors by spreading them evenly across the Evaluation Slice.
- Ensure anchors leave enough room for a full evaluation episode.
- Reuse the exact same Evaluation Spec for every Generation in the Run.

### 3. Seeds and reproducibility

- Persist a `Training Seed` for the Run.
- Persist an `Evaluation Seed` for the Run.
- Ensure evaluation uses deterministic prediction and deterministic episode starts from the fixed anchors.
- Make it possible to replay an Evaluation Pass later from persisted metadata alone.

### 4. Trainer changes

- Stop using the same env/data source for both learning and evaluation.
- Introduce a training env built from `Training Slice`.
- Introduce an evaluation path built from `Evaluation Slice` plus `Evaluation Spec`.
- Compute `Training Sharpe` separately from `Evaluation Sharpe`.
- Compute `Evaluation Sharpe` as the average Sharpe across all evaluation-anchor episodes.
- Keep per-anchor evaluation results, not just the merged average.

### 5. Promotion gate

- Promotion decision must check:
  - `Evaluation Sharpe` beats current `Best Evaluation Sharpe` by `promote_threshold`
  - minimum `Executed Trade` count is satisfied
  - minimum SELL-side realized exits is satisfied
- Define the activity thresholds as fixed numeric values.
- Keep thresholds intentionally loose for Milestone 1.
- Do not add extra promotion conditions like PnL/drawdown yet.

### 6. Evaluation record persistence

- Persist one `Evaluation Record` per Generation.
- Each Evaluation Record should store at least:
  - generation number
  - Evaluation Sharpe
  - Best Evaluation Sharpe after evaluation
  - Executed Trade count used by the gate
  - SELL realized-exit count used by the gate
  - promotion passed or failed
  - human-readable gate reasons
  - per-anchor detail
- Keep enough information to inspect why a Generation did or did not promote.

### 7. Event and API contract

- Update `training_update` payloads so training metrics and evaluation metrics are distinct.
- Expose explicit fields for:
  - Training Sharpe
  - Evaluation Sharpe
  - Best Evaluation Sharpe
  - promotion gate outcome
  - promotion gate reasons
- Avoid ambiguous labels like a naked `sharpe` when the meaning is really evaluation-only.
- Keep existing live-step streaming behavior intact unless a change is required for the new summary fields.

### 8. UI changes

- Show `Training Sharpe` and `Evaluation Sharpe` separately in the dashboard.
- Label `best_sharpe` as `Best Evaluation Sharpe` in the UI.
- Show whether a Generation passed or failed the Promotion Gate.
- Show clear gate reasons, for example:
  - "Evaluation Sharpe did not beat best"
  - "Executed Trade count below minimum"
  - "SELL realized exits below minimum"
- Keep these explanations visible in places where users inspect Run progress/history.

### 9. Logging and observability

- Log the Evaluation Spec at Run start.
- Log per-Generation Training Sharpe and Evaluation Sharpe separately.
- Log promotion gate inputs and pass/fail reasons per Generation.
- Log when a checkpoint is promoted because the full gate passed.
- Log when a checkpoint is not promoted and why.

### 10. Tests

- Add unit tests for chronological slice splitting.
- Add unit tests for even anchor generation.
- Add unit tests proving evaluation reuses the same anchors across Generations in a Run.
- Add unit tests for promotion gate pass/fail behavior.
- Add unit tests for separate Training Sharpe vs Evaluation Sharpe fields.
- Add persistence tests for Evaluation Spec, seeds, and Evaluation Record.
- Add API/event-mapper tests for the new summary payload shape.
- Add UI tests that verify labels and failure reasons are rendered clearly.
- Add at least one integration test showing promotion uses out-of-sample evaluation rather than in-sample training metrics.

## Suggested delivery order

1. Slice split + Evaluation Spec + seeds
2. Trainer evaluation rewrite
3. Promotion Gate logic
4. Persistence for Evaluation Spec and Evaluation Record
5. Event/API contract updates
6. UI labels and gate-reason visibility
7. Final integration tests

## Done when

- A Run can be inspected later and we can answer:
  - what data was used for training
  - what data was used for evaluation
  - which anchors were used
  - which seeds were used
  - how each Generation performed per anchor
  - why a checkpoint did or did not promote
- `best.zip` promotion is based on fixed out-of-sample evaluation, not the training slice.
- Dashboard and logs no longer blur training metrics and evaluation metrics together.
