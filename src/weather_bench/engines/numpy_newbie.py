"""numpy - NEWBIE: authentic naive numpy with Python loops for groupby and join.

A beginner learning numpy might load data into per-column arrays but still use
Python loops for operations like groupby and join (since numpy has no native
support). This case shows that authentic learning path: minimal numpy, maximum
handwritten loops.
"""

from __future__ import annotations

import numpy as np

from weather_bench.common.contract import normalize
from weather_bench.common.schema import (
    FILTER_HUMIDITY_MAX,
    FILTER_TEMP_MIN,
    CanonicalResult,
    RawTable,
)


class NumpyNewbiePipeline:
    name = "numpy-newbie"

    def load(self, weather: RawTable, stations: RawTable) -> dict:
        """Load raw tables into a dict with per-column numpy arrays or lists."""
        state = {
            "weather": {
                "station_id": np.array(weather["station_id"], dtype=np.int64),
                "temperature": np.array(weather["temperature"], dtype=np.float64),
                "humidity": np.array(weather["humidity"], dtype=np.float64),
                "precipitation": np.array(weather["precipitation"], dtype=np.float64),
            },
            "stations": stations,  # Keep as dict of lists for dimension
        }
        return state

    def filter(self, state: dict) -> dict:
        """Filter rows: temperature > 20 AND humidity < 80 using Python loop."""
        weather = state["weather"]
        n_rows = len(weather["station_id"])

        # Naive: loop row-by-row, append to new lists
        filtered_station_id = []
        filtered_temperature = []
        filtered_humidity = []
        filtered_precipitation = []

        for i in range(n_rows):
            temp = float(weather["temperature"][i])
            hum = float(weather["humidity"][i])
            if temp > FILTER_TEMP_MIN and hum < FILTER_HUMIDITY_MAX:
                filtered_station_id.append(int(weather["station_id"][i]))
                filtered_temperature.append(temp)
                filtered_humidity.append(hum)
                filtered_precipitation.append(float(weather["precipitation"][i]))

        # Convert back to numpy arrays
        state["weather"] = {
            "station_id": np.array(filtered_station_id, dtype=np.int64),
            "temperature": np.array(filtered_temperature, dtype=np.float64),
            "humidity": np.array(filtered_humidity, dtype=np.float64),
            "precipitation": np.array(filtered_precipitation, dtype=np.float64),
        }
        return state

    def aggregate(self, state: dict) -> dict:
        """Aggregate by station_id using nested dict loop (no groupby)."""
        weather = state["weather"]
        n_rows = len(weather["station_id"])

        # Naive: manual dict-based accumulation
        agg_data = {}

        for i in range(n_rows):
            station_id = int(weather["station_id"][i])
            temp = float(weather["temperature"][i])
            hum = float(weather["humidity"][i])
            precip = float(weather["precipitation"][i])

            if station_id not in agg_data:
                agg_data[station_id] = {
                    "temp_sum": 0.0,
                    "temp_count": 0,
                    "max_humidity": hum,
                    "precip_sum": 0.0,
                }

            agg_data[station_id]["temp_sum"] += temp
            agg_data[station_id]["temp_count"] += 1
            agg_data[station_id]["max_humidity"] = max(agg_data[station_id]["max_humidity"], hum)
            agg_data[station_id]["precip_sum"] += precip

        # Convert to lists for next step
        state["agg_data"] = agg_data
        return state

    def join(self, state: dict) -> dict:
        """Join agg_data with stations dimension using Python loop and dict lookup."""
        agg_data = state["agg_data"]
        stations_table = state["stations"]

        # Build station_id -> (station_name, climate_zone) lookup
        station_lookup = {}
        for i in range(len(stations_table["station_id"])):
            sid = stations_table["station_id"][i]
            station_lookup[sid] = (
                stations_table["station_name"][i],
                stations_table["climate_zone"][i],
            )

        # Join: loop agg_data and lookup station info
        joined_rows = []
        for station_id, agg in agg_data.items():
            if station_id in station_lookup:  # inner join
                station_name, climate_zone = station_lookup[station_id]
                mean_temp = agg["temp_sum"] / agg["temp_count"] if agg["temp_count"] > 0 else 0.0
                row = (
                    station_id,
                    station_name,
                    climate_zone,
                    mean_temp,
                    agg["max_humidity"],
                    agg["precip_sum"],
                    agg["temp_count"],
                )
                joined_rows.append(row)

        state["joined_rows"] = joined_rows
        return state

    def sort(self, state: dict) -> dict:
        """Sort by total_precip DESC then station_id ASC using Python sorted()."""
        joined_rows = state["joined_rows"]
        # Naive Python sort: key is (neg precip for DESC, station_id for ASC)
        sorted_rows = sorted(joined_rows, key=lambda r: (-r[5], r[0]))
        state["sorted_rows"] = sorted_rows
        return state

    def materialize(self, state: dict) -> CanonicalResult:
        """Build canonical result and apply normalize for rounding and final sort."""
        sorted_rows = state["sorted_rows"]
        # sorted_rows are already tuples matching CanonicalRow shape
        return normalize(sorted_rows)
