"""pandas - PRO: vectorized operations with method chaining.

Idiomatic pandas implementation using boolean indexing, groupby().agg(),
and pd.merge() to chain operations. No row loops in critical path.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from weather_bench.common.contract import normalize
from weather_bench.common.schema import (
    FILTER_HUMIDITY_MAX,
    FILTER_TEMP_MIN,
    CanonicalResult,
    RawTable,
)


class PandasProPipeline:
    name = "pandas-pro"

    def load(self, weather: RawTable, stations: RawTable) -> tuple[pd.DataFrame, pd.DataFrame]:
        return pd.DataFrame(weather), pd.DataFrame(stations)

    def filter(self, state: tuple[pd.DataFrame, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
        weather, stations = state
        weather = weather[
            (weather["temperature"] > FILTER_TEMP_MIN) & (weather["humidity"] < FILTER_HUMIDITY_MAX)
        ]
        return weather, stations

    def aggregate(
        self, state: tuple[pd.DataFrame, pd.DataFrame]
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        weather, stations = state
        weather = weather.groupby("station_id", as_index=False).agg(
            mean_temp=("temperature", "mean"),
            max_humidity=("humidity", "max"),
            total_precip=("precipitation", "sum"),
            n=("temperature", "size"),
        )
        return weather, stations

    def join(self, state: tuple[pd.DataFrame, pd.DataFrame]) -> pd.DataFrame:
        weather, stations = state
        return pd.merge(
            weather,
            stations[["station_id", "station_name", "climate_zone"]],
            on="station_id",
            how="inner",
        )

    def sort(self, state: pd.DataFrame) -> pd.DataFrame:
        return state.sort_values(["total_precip", "station_id"], ascending=[False, True])

    def materialize(self, state: pd.DataFrame) -> CanonicalResult:
        rows = [
            (
                cast(int, r.station_id),
                cast(str, r.station_name),
                cast(str, r.climate_zone),
                cast(float, r.mean_temp),
                cast(float, r.max_humidity),
                cast(float, r.total_precip),
                cast(int, r.n),
            )
            for r in state.itertuples(index=False)
        ]
        return normalize(rows)
