from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import math
import secrets
from typing import Any

import pandas as pd


DEFAULT_EVALUATION_HOLDOUT_RATIO = 0.2
DEFAULT_EVALUATION_ANCHOR_COUNT = 4


@dataclass(frozen=True)
class RunEvaluationPlan:
    training_data: pd.DataFrame
    evaluation_data: pd.DataFrame
    evaluation_spec: dict[str, Any]


def _timestamp_for_index(data: pd.DataFrame, index: int) -> str | None:
    if index < 0 or index >= len(data):
        return None
    raw = data.iloc[index].get('timestamp')
    if raw is None or pd.isna(raw):
        return None
    return datetime.fromtimestamp(float(raw) / 1000.0, tz=UTC).isoformat()


def _slice_metadata(data: pd.DataFrame, start_index: int, end_index: int) -> dict[str, Any]:
    candle_count = (end_index - start_index) + 1
    return {
        'start_index': start_index,
        'end_index': end_index,
        'start_timestamp': _timestamp_for_index(data, start_index),
        'end_timestamp': _timestamp_for_index(data, end_index),
        'candle_count': candle_count,
    }


def _minimum_slice_candles(window_size: int, episode_length: int) -> int:
    return window_size + episode_length


def _derive_slice_boundaries(
    total_candles: int,
    window_size: int,
    episode_length: int,
    holdout_ratio: float,
    anchor_count: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    minimum_training = _minimum_slice_candles(window_size, episode_length)
    minimum_evaluation = minimum_training + max(anchor_count - 1, 0)
    if total_candles < minimum_training + minimum_evaluation:
        raise ValueError('not enough candles to create separate training and evaluation slices')

    evaluation_candles = max(int(math.ceil(total_candles * holdout_ratio)), minimum_evaluation)
    training_candles = total_candles - evaluation_candles
    if training_candles < minimum_training:
        evaluation_candles = total_candles - minimum_training
        training_candles = total_candles - evaluation_candles

    training_range = (0, training_candles - 1)
    evaluation_range = (training_candles, total_candles - 1)
    return training_range, evaluation_range


def _anchor_offsets(max_start_offset: int, desired_count: int) -> list[int]:
    actual_count = min(desired_count, max_start_offset + 1)
    if actual_count <= 1:
        return [0]

    offsets: list[int] = []
    used: set[int] = set()
    for idx in range(actual_count):
        offset = int(round((idx * max_start_offset) / (actual_count - 1)))
        if offset not in used:
            offsets.append(offset)
            used.add(offset)

    candidate = 0
    while len(offsets) < actual_count:
        if candidate not in used:
            offsets.append(candidate)
            used.add(candidate)
        candidate += 1

    return sorted(offsets)


def _build_anchor_metadata(
    data: pd.DataFrame,
    evaluation_start_index: int,
    evaluation_candles: int,
    window_size: int,
    episode_length: int,
    anchor_count: int,
) -> list[dict[str, Any]]:
    max_start_offset = evaluation_candles - window_size - episode_length
    if max_start_offset < 0:
        raise ValueError('evaluation slice does not leave enough room for an evaluation episode')

    anchors: list[dict[str, Any]] = []
    for idx, offset in enumerate(_anchor_offsets(max_start_offset, anchor_count), start=1):
        absolute_index = evaluation_start_index + offset
        anchors.append(
            {
                'label': f'A{idx}',
                'start_index': offset,
                'start_timestamp': _timestamp_for_index(data, absolute_index),
            }
        )
    return anchors


def build_run_evaluation_plan(
    config: dict[str, Any],
    data: pd.DataFrame,
    training_seed: int | None = None,
    evaluation_seed: int | None = None,
    holdout_ratio: float = DEFAULT_EVALUATION_HOLDOUT_RATIO,
    anchor_count: int = DEFAULT_EVALUATION_ANCHOR_COUNT,
) -> RunEvaluationPlan:
    window_size = int(config['data']['window_size'])
    episode_length = int(config['env']['episode_length'])
    training_seed = secrets.randbelow(2**31) if training_seed is None else int(training_seed)
    evaluation_seed = secrets.randbelow(2**31) if evaluation_seed is None else int(evaluation_seed)

    training_range, evaluation_range = _derive_slice_boundaries(
        total_candles=len(data),
        window_size=window_size,
        episode_length=episode_length,
        holdout_ratio=holdout_ratio,
        anchor_count=anchor_count,
    )
    training_start, training_end = training_range
    evaluation_start, evaluation_end = evaluation_range

    evaluation_candles = (evaluation_end - evaluation_start) + 1
    anchors = _build_anchor_metadata(
        data=data,
        evaluation_start_index=evaluation_start,
        evaluation_candles=evaluation_candles,
        window_size=window_size,
        episode_length=episode_length,
        anchor_count=anchor_count,
    )

    evaluation_spec = {
        'training_slice': _slice_metadata(data, training_start, training_end),
        'evaluation_slice': _slice_metadata(data, evaluation_start, evaluation_end),
        'evaluation_anchors': anchors,
        'evaluation_episode_length': episode_length,
        'training_seed': training_seed,
        'evaluation_seed': evaluation_seed,
    }
    return RunEvaluationPlan(
        training_data=data.iloc[training_start : training_end + 1].reset_index(drop=True),
        evaluation_data=data.iloc[evaluation_start : evaluation_end + 1].reset_index(drop=True),
        evaluation_spec=evaluation_spec,
    )


def build_synthetic_run_evaluation_plan(config: dict[str, Any]) -> RunEvaluationPlan:
    total_candles = 2_000
    rows = [
        [1700000000000 + i * 900_000, 30_000 + i, 30_050 + i, 29_950 + i, 30_010 + i, 100 + i]
        for i in range(total_candles)
    ]
    data = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return build_run_evaluation_plan(config=config, data=data)
