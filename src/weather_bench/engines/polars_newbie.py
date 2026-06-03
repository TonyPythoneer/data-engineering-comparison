"""polars - NEWBIE: eager DataFrames at every step (naive, no fusion).

Beginner's polars. Uses the eager API: create concrete DataFrames immediately,
materialize results at every step. No query optimization, no LazyFrame plans.
This shows the cost penalty of eager evaluation without fusion.
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


class PolarsNewbiePipeline:
    name = "polars-newbie"

    def load(self, weather: RawTable, stations: RawTable) -> tuple[pl.DataFrame, pl.DataFrame]:
        return pl.DataFrame(weather), pl.DataFrame(stations)

    def filter(self, state: tuple[pl.DataFrame, pl.DataFrame]) -> tuple[pl.DataFrame, pl.DataFrame]:
        weather, stations = state
        weather = weather.filter(
            (pl.col("temperature") > FILTER_TEMP_MIN) & (pl.col("humidity") < FILTER_HUMIDITY_MAX)
        )
        return weather, stations

    def aggregate(
        self, state: tuple[pl.DataFrame, pl.DataFrame]
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        weather, stations = state
        weather = weather.group_by("station_id").agg(
            pl.col("temperature").mean().alias("mean_temp"),
            pl.col("humidity").max().alias("max_humidity"),
            pl.col("precipitation").sum().alias("total_precip"),
            pl.len().alias("n"),
        )
        return weather, stations

    def join(self, state: tuple[pl.DataFrame, pl.DataFrame]) -> pl.DataFrame:
        weather, stations = state
        return weather.join(
            stations.select("station_id", "station_name", "climate_zone"),
            on="station_id",
            how="inner",
        )

    def sort(self, state: pl.DataFrame) -> pl.DataFrame:
        return state.sort(by=["total_precip", "station_id"], descending=[True, False])

    def materialize(self, state: pl.DataFrame) -> CanonicalResult:
        rows = [
            (
                r["station_id"],
                r["station_name"],
                r["climate_zone"],
                r["mean_temp"],
                r["max_humidity"],
                r["total_precip"],
                r["n"],
            )
            for r in state.iter_rows(named=True)
        ]
        return normalize(rows)
