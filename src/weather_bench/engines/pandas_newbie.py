"""pandas - NEWBIE: authentic naive pandas with chained indexing and manual loops.

A beginner learning pandas might create DataFrames but still rely on Python loops
for groupby and join operations, or use chained boolean indexing (the classic newbie
smell). This case shows that learning path: DataFrames + loops instead of .groupby()
and .merge().
"""

from __future__ import annotations

import pandas as pd

from weather_bench.common.contract import normalize
from weather_bench.common.schema import (
    FILTER_HUMIDITY_MAX,
    FILTER_TEMP_MIN,
    CanonicalResult,
    RawTable,
)


class PandasNewbiePipeline:
    name = "pandas-newbie"

    def load(self, weather: RawTable, stations: RawTable) -> dict:
        """Load raw tables into pandas DataFrames."""
        state = {
            "weather_df": pd.DataFrame(weather),
            "stations_df": pd.DataFrame(stations),
        }
        return state

    def filter(self, state: dict) -> dict:
        """Filter rows: temperature > 20 AND humidity < 80 using chained indexing."""
        weather_df = state["weather_df"]
        # Naive chained indexing: two separate boolean masks applied sequentially
        temp_mask = weather_df["temperature"] > FILTER_TEMP_MIN
        humidity_mask = weather_df["humidity"] < FILTER_HUMIDITY_MAX
        # Combine masks with & operator (chained indexing style)
        filtered_df = weather_df[temp_mask & humidity_mask].copy()
        state["weather_df"] = filtered_df
        return state

    def aggregate(self, state: dict) -> dict:
        """Aggregate by station_id using manual loop over unique station IDs."""
        weather_df = state["weather_df"]
        # Naive: get unique station_ids and loop manually
        unique_stations = weather_df["station_id"].unique()

        rows = []
        for station_id in unique_stations:
            # Slice df for this station (another newbie pattern)
            station_data = weather_df[weather_df["station_id"] == station_id]

            # Compute aggregations manually using pandas Series methods
            mean_temp = station_data["temperature"].mean()
            max_humidity = station_data["humidity"].max()
            total_precip = station_data["precipitation"].sum()
            n = len(station_data)

            rows.append(
                {
                    "station_id": station_id,
                    "mean_temp": mean_temp,
                    "max_humidity": max_humidity,
                    "total_precip": total_precip,
                    "n": n,
                }
            )

        # Build DataFrame from list of dicts
        state["agg_df"] = pd.DataFrame(rows)
        return state

    def join(self, state: dict) -> dict:
        """Join agg_df with stations using manual lookup loop."""
        agg_df = state["agg_df"]
        stations_df = state["stations_df"]

        # Naive: manual loop joining instead of .merge()
        joined_rows = []
        for _, agg_row in agg_df.iterrows():
            station_id = agg_row["station_id"]
            # Manual lookup: filter stations_df to find matching row
            station_info = stations_df[stations_df["station_id"] == station_id]

            if len(station_info) > 0:  # inner join condition
                station_name = station_info.iloc[0]["station_name"]
                climate_zone = station_info.iloc[0]["climate_zone"]

                joined_rows.append(
                    {
                        "station_id": station_id,
                        "station_name": station_name,
                        "climate_zone": climate_zone,
                        "mean_temp": agg_row["mean_temp"],
                        "max_humidity": agg_row["max_humidity"],
                        "total_precip": agg_row["total_precip"],
                        "n": agg_row["n"],
                    }
                )

        state["joined_df"] = pd.DataFrame(joined_rows)
        return state

    def sort(self, state: dict) -> dict:
        """Sort by total_precip DESC, station_id ASC using sort_values."""
        joined_df = state["joined_df"]
        # Newbie: use sort_values with by list
        sorted_df = joined_df.sort_values(
            by=["total_precip", "station_id"],
            ascending=[False, True],
        ).reset_index(drop=True)
        state["sorted_df"] = sorted_df
        return state

    def materialize(self, state: dict) -> CanonicalResult:
        """Build canonical result from sorted DataFrame and apply normalize."""
        sorted_df = state["sorted_df"]
        # Convert DataFrame rows to tuples in RESULT_COLUMNS order
        rows = [
            (
                int(row["station_id"]),
                str(row["station_name"]),
                str(row["climate_zone"]),
                float(row["mean_temp"]),
                float(row["max_humidity"]),
                float(row["total_precip"]),
                int(row["n"]),
            )
            for _, row in sorted_df.iterrows()
        ]
        return normalize(rows)
