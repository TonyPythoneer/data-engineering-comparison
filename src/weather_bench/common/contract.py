"""The shared pipeline contract every engine case implements.

A case carries opaque per-engine ``State`` (a DataFrame, a dict of arrays, a
DuckDB relation, ...) through six steps. The harness never inspects the state;
it only times each step and compares the final ``materialize`` output.

Fixed, identical semantics across all six cases:
  - filter      : temperature > 20 AND humidity < 80
  - aggregate   : group by station_id -> mean_temp, max_humidity, total_precip, n
  - join        : enrich with station_name, climate_zone from the dimension
  - sort        : total_precip DESC, station_id ASC (tie-break for determinism)
  - materialize : force evaluation -> canonical rows (lazy engines pay here)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from weather_bench.common.schema import (
    ROUND_DECIMALS,
    CanonicalResult,
    CanonicalRow,
    RawTable,
)


@runtime_checkable
class Pipeline(Protocol):
    """Engine case contract. ``State`` is engine-specific and opaque."""

    name: str

    def load(self, weather: RawTable, stations: RawTable) -> Any: ...
    def filter(self, state: Any) -> Any: ...
    def aggregate(self, state: Any) -> Any: ...
    def join(self, state: Any) -> Any: ...
    def sort(self, state: Any) -> Any: ...
    def materialize(self, state: Any) -> CanonicalResult: ...


def run_pipeline(pipeline: Pipeline, weather: RawTable, stations: RawTable) -> CanonicalResult:
    """Run all steps end-to-end and return the materialized canonical result."""
    state = pipeline.load(weather, stations)
    state = pipeline.filter(state)
    state = pipeline.aggregate(state)
    state = pipeline.join(state)
    state = pipeline.sort(state)
    return pipeline.materialize(state)


def normalize(rows: list[CanonicalRow]) -> CanonicalResult:
    """Round floats and re-sort so cross-engine output is byte-comparable.

    Engines may differ in float formatting and stable-sort behaviour; this
    pins both. Sort key matches the contract: total_precip DESC, station_id ASC.
    """
    rounded: CanonicalResult = [
        (
            int(station_id),
            str(station_name),
            str(climate_zone),
            round(float(mean_temp), ROUND_DECIMALS),
            round(float(max_humidity), ROUND_DECIMALS),
            round(float(total_precip), ROUND_DECIMALS),
            int(n),
        )
        for (
            station_id,
            station_name,
            climate_zone,
            mean_temp,
            max_humidity,
            total_precip,
            n,
        ) in rows
    ]
    rounded.sort(key=lambda r: (-r[5], r[0]))
    return rounded
