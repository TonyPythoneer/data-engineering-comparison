"""In-process per-operation timing (secondary to the pytest-benchmark headline).

Per-op isolation across stateful engines (e.g. duckdb-newbie's temp tables)
cannot be expressed as independent pytest-benchmark fixtures, so the per-op
breakdown is measured here: each round runs a fresh pipeline end-to-end,
timestamping after every step; per-step cost is the difference. The minimum
across rounds is the robust estimate (least contaminated by jitter/GC).

For lazy engines (polars-pro, duckdb-pro) the transform steps cost ~0 and
``materialize`` carries the work — that asymmetry is the point, and it shows.
"""

from __future__ import annotations

from collections.abc import Callable
from statistics import median
from time import perf_counter

from weather_bench.common.contract import Pipeline
from weather_bench.common.schema import STEP_NAMES, RawTable

# Fewer rounds as data grows (each round costs more); enough for a stable min.
ROUNDS_BY_SIZE = {50: 200, 500: 100, 5000: 30}


def _run_steps_timed(pipeline: Pipeline, weather: RawTable, stations: RawTable) -> list[float]:
    """Run one full pipeline, returning per-step durations in STEP_NAMES order."""
    marks = [perf_counter()]
    state = pipeline.load(weather, stations)
    marks.append(perf_counter())
    state = pipeline.filter(state)
    marks.append(perf_counter())
    state = pipeline.aggregate(state)
    marks.append(perf_counter())
    state = pipeline.join(state)
    marks.append(perf_counter())
    state = pipeline.sort(state)
    marks.append(perf_counter())
    pipeline.materialize(state)
    marks.append(perf_counter())
    return [marks[i + 1] - marks[i] for i in range(len(STEP_NAMES))]


def time_steps(
    make_pipeline: Callable[[], Pipeline],
    weather: RawTable,
    stations: RawTable,
    rounds: int,
) -> dict[str, dict[str, float]]:
    """Time each step over ``rounds`` fresh runs; return min/median per step + total."""
    make_pipeline()  # warmup (imports, first-call compilation)
    _run_steps_timed(make_pipeline(), weather, stations)

    samples: list[list[float]] = [
        _run_steps_timed(make_pipeline(), weather, stations) for _ in range(rounds)
    ]

    out: dict[str, dict[str, float]] = {}
    for i, step in enumerate(STEP_NAMES):
        col = [row[i] for row in samples]
        out[step] = {"min": min(col), "median": median(col)}
    totals = [sum(row) for row in samples]
    out["total"] = {"min": min(totals), "median": median(totals)}
    return out
