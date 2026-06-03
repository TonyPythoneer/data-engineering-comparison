"""Seeded synthetic weather data generator.

Engine-neutral output: columnar dicts of plain Python scalars (no numpy / polars
types leak out), so every engine loads from an identical starting point. Same
seed + same row count => identical data, guaranteeing a fair, reproducible run.
"""

from __future__ import annotations

import numpy as np

from weather_bench.common.schema import RawTable

# Ten fixed weather stations form the join dimension.
N_STATIONS = 10

_STATION_NAMES = (
    "Aurora",
    "Brookfield",
    "Cedar Falls",
    "Dunmore",
    "Eastport",
    "Fairview",
    "Glenwood",
    "Harborton",
    "Ironwood",
    "Junction City",
)
_CLIMATE_ZONES = (
    "temperate",
    "continental",
    "coastal",
    "arid",
    "alpine",
)


def generate_weather(n_rows: int, seed: int = 42) -> RawTable:
    """Return a weather fact table with ``n_rows`` reproducible rows."""
    rng = np.random.default_rng(seed)
    return {
        "station_id": rng.integers(0, N_STATIONS, size=n_rows).tolist(),
        "date": (np.arange(n_rows) % 365).tolist(),
        "temperature": rng.normal(15.0, 10.0, n_rows).round(2).tolist(),
        "humidity": rng.uniform(10.0, 100.0, n_rows).round(2).tolist(),
        "precipitation": rng.exponential(2.0, n_rows).round(2).tolist(),
        "wind_speed": rng.uniform(0.0, 30.0, n_rows).round(2).tolist(),
    }


def generate_stations() -> RawTable:
    """Return the static station dimension table (always ``N_STATIONS`` rows)."""
    rng = np.random.default_rng(0)
    return {
        "station_id": list(range(N_STATIONS)),
        "station_name": list(_STATION_NAMES),
        "latitude": rng.uniform(-60.0, 60.0, N_STATIONS).round(4).tolist(),
        "longitude": rng.uniform(-180.0, 180.0, N_STATIONS).round(4).tolist(),
        "elevation_m": rng.integers(0, 3000, N_STATIONS).tolist(),
        "climate_zone": [_CLIMATE_ZONES[i % len(_CLIMATE_ZONES)] for i in range(N_STATIONS)],
    }
