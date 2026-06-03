"""polars - PRO: a single lazy chain; the query optimizer fuses the steps.

Reference implementation. Each transform step only *extends* a ``LazyFrame``
plan (near-zero cost); all real work happens in ``materialize`` at ``.collect()``.
That is the point of the lazy API and shows up in the per-op timing.
"""

from __future__ import annotations

import polars as pl

from weather_bench.common.contract import normalize
from weather_bench.common.schema import (
    FILTER_HUMIDITY_MAX,
    FILTER_TEMP_MIN,
    CanonicalResult,
    RawTable,
)


class PolarsProPipeline:
    name = "polars-pro"

    def load(self, weather: RawTable, stations: RawTable) -> tuple[pl.LazyFrame, pl.LazyFrame]:
        return pl.LazyFrame(weather), pl.LazyFrame(stations)

    def filter(self, state: tuple[pl.LazyFrame, pl.LazyFrame]) -> tuple[pl.LazyFrame, pl.LazyFrame]:
        weather, stations = state
        weather = weather.filter(
            (pl.col("temperature") > FILTER_TEMP_MIN) & (pl.col("humidity") < FILTER_HUMIDITY_MAX)
        )
        return weather, stations

    def aggregate(
        self, state: tuple[pl.LazyFrame, pl.LazyFrame]
    ) -> tuple[pl.LazyFrame, pl.LazyFrame]:
        weather, stations = state
        weather = weather.group_by("station_id").agg(
            pl.col("temperature").mean().alias("mean_temp"),
            pl.col("humidity").max().alias("max_humidity"),
            pl.col("precipitation").sum().alias("total_precip"),
            pl.len().alias("n"),
        )
        return weather, stations

    def join(self, state: tuple[pl.LazyFrame, pl.LazyFrame]) -> pl.LazyFrame:
        weather, stations = state
        return weather.join(
            stations.select("station_id", "station_name", "climate_zone"),
            on="station_id",
            how="inner",
        )

    def sort(self, state: pl.LazyFrame) -> pl.LazyFrame:
        return state.sort(by=["total_precip", "station_id"], descending=[True, False])

    def materialize(self, state: pl.LazyFrame) -> CanonicalResult:
        # Select into RESULT_COLUMNS order, then extract tuples directly with
        # .rows() — avoids building a Python dict per row (iter_rows(named=True)).
        df = state.collect().select(
            "station_id",
            "station_name",
            "climate_zone",
            "mean_temp",
            "max_humidity",
            "total_precip",
            "n",
        )
        return normalize(df.rows())
