"""numpy - PRO: fully vectorized numpy operations with no Python loops.

Idiomatic vectorized numpy:
  - load: store each column as float64 (numeric) or int64 (station_id)
  - filter: boolean mask, fancy-index all arrays
  - aggregate: np.unique + np.bincount for group-by operations
  - join: vectorized lookup using station_id as index into stations arrays
  - sort: np.lexsort for multi-key sort (DESC total_precip, ASC station_id)
  - materialize: zip arrays into rows and normalize
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


class NumpyProPipeline:
    name = "numpy-pro"

    def load(
        self,
        weather: RawTable,
        stations: RawTable,
    ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        """Load RawTable into dict of numpy arrays; numeric -> float64, ids -> int64."""
        weather_arrays = {
            "station_id": np.array(weather["station_id"], dtype=np.int64),
            "date": np.array(weather["date"], dtype=np.int64),
            "temperature": np.array(weather["temperature"], dtype=np.float64),
            "humidity": np.array(weather["humidity"], dtype=np.float64),
            "precipitation": np.array(weather["precipitation"], dtype=np.float64),
            "wind_speed": np.array(weather["wind_speed"], dtype=np.float64),
        }

        stations_arrays = {
            "station_id": np.array(stations["station_id"], dtype=np.int64),
            "station_name": np.array(stations["station_name"], dtype=object),
            "latitude": np.array(stations["latitude"], dtype=np.float64),
            "longitude": np.array(stations["longitude"], dtype=np.float64),
            "elevation_m": np.array(stations["elevation_m"], dtype=np.int64),
            "climate_zone": np.array(stations["climate_zone"], dtype=object),
        }

        return weather_arrays, stations_arrays

    def filter(
        self,
        state: tuple[dict[str, np.ndarray], dict[str, np.ndarray]],
    ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        """Apply boolean mask: temperature > 20 AND humidity < 80."""
        weather, stations = state
        mask = (weather["temperature"] > FILTER_TEMP_MIN) & (
            weather["humidity"] < FILTER_HUMIDITY_MAX
        )
        filtered = {k: v[mask] for k, v in weather.items()}
        return filtered, stations

    def aggregate(
        self,
        state: tuple[dict[str, np.ndarray], dict[str, np.ndarray]],
    ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        """Group by station_id using np.unique + np.bincount for aggregations."""
        weather, stations = state
        station_id = weather["station_id"]
        temperature = weather["temperature"]
        humidity = weather["humidity"]
        precipitation = weather["precipitation"]

        # Get unique station_ids and reverse indices for group membership
        unique_ids, inverse_indices = np.unique(station_id, return_inverse=True)

        # Aggregate: count per group
        n_per_group = np.bincount(inverse_indices)

        # Mean temperature: sum / count
        temp_sum = np.bincount(inverse_indices, weights=temperature)
        mean_temp = temp_sum / n_per_group

        # Max humidity per group: use np.maximum.at on a preallocated array
        max_humidity = np.full(len(unique_ids), -np.inf, dtype=np.float64)
        np.maximum.at(max_humidity, inverse_indices, humidity)

        # Total precipitation per group
        total_precip = np.bincount(inverse_indices, weights=precipitation)

        # Build aggregated state
        agg_arrays = {
            "station_id": unique_ids,
            "mean_temp": mean_temp,
            "max_humidity": max_humidity,
            "total_precip": total_precip,
            "n": n_per_group,
        }

        return agg_arrays, stations

    def join(
        self,
        state: tuple[dict[str, np.ndarray], dict[str, np.ndarray]],
    ) -> dict[str, np.ndarray]:
        """Inner join on station_id; lookup station_name and climate_zone."""
        agg, stations = state
        agg_station_id = agg["station_id"]

        # Build lookup arrays indexed by station_id (safe for small range)
        # Size by the dimension table's max id (every station exists there),
        # not the aggregated subset — at small row counts some stations may be
        # absent post-filter, which would otherwise undersize the lookup.
        max_id = int(np.max(stations["station_id"])) + 1
        lookup_names = np.empty(max_id, dtype=object)
        lookup_zones = np.empty(max_id, dtype=object)

        for i, sid in enumerate(stations["station_id"]):
            lookup_names[sid] = stations["station_name"][i]
            lookup_zones[sid] = stations["climate_zone"][i]

        # Vectorized lookup for each aggregated station_id
        station_names = lookup_names[agg_station_id]
        climate_zones = lookup_zones[agg_station_id]

        return {
            "station_id": agg_station_id,
            "station_name": station_names,
            "climate_zone": climate_zones,
            "mean_temp": agg["mean_temp"],
            "max_humidity": agg["max_humidity"],
            "total_precip": agg["total_precip"],
            "n": agg["n"],
        }

    def sort(
        self,
        state: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        """Sort by total_precip DESC, station_id ASC using np.lexsort."""
        # lexsort: rightmost key is primary, all keys ascending by default
        # For DESC total_precip, negate it; for ASC station_id, use as-is
        order = np.lexsort((state["station_id"], -state["total_precip"]))

        sorted_state = {k: v[order] for k, v in state.items()}
        return sorted_state

    def materialize(self, state: dict[str, np.ndarray]) -> CanonicalResult:
        """Convert arrays to list of canonical rows and normalize."""
        rows = [
            (
                int(state["station_id"][i]),
                str(state["station_name"][i]),
                str(state["climate_zone"][i]),
                float(state["mean_temp"][i]),
                float(state["max_humidity"][i]),
                float(state["total_precip"][i]),
                int(state["n"][i]),
            )
            for i in range(len(state["station_id"]))
        ]
        return normalize(rows)
