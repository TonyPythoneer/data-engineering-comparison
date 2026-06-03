"""Shared schema: column names, op parameters, and the canonical result type.

Every engine case consumes the same engine-neutral input (``RawTable`` = a
columnar dict of plain Python lists) and produces the same ``CanonicalResult``
so that all six implementations can be checked for byte-identical output.
"""

from __future__ import annotations

# Engine-neutral input: column name -> list of values (columnar layout).
RawTable = dict[str, list]

# --- Weather fact table columns ---------------------------------------------
WEATHER_COLUMNS = (
    "station_id",
    "date",  # int day-index since an arbitrary epoch; ops do not parse it
    "temperature",
    "humidity",
    "precipitation",
    "wind_speed",
)

# --- Station dimension columns ----------------------------------------------
STATION_COLUMNS = (
    "station_id",
    "station_name",
    "latitude",
    "longitude",
    "elevation_m",
    "climate_zone",
)

# --- Fixed, identical-across-engines operation parameters -------------------
FILTER_TEMP_MIN = 20.0  # keep rows with temperature > 20
FILTER_HUMIDITY_MAX = 80.0  # AND humidity < 80

# Float rounding for FP-stable equivalence comparison across engines.
ROUND_DECIMALS = 6

# The five logical pipeline steps plus the forced-materialization step.
# Lazy engines (polars-pro, duckdb-pro) attribute almost all cost to
# "materialize"; eager engines spread it across the transform steps. That
# contrast is intentional and shows up directly in the per-op report.
STEP_NAMES = ("load", "filter", "aggregate", "join", "sort", "materialize")

# Columns of one canonical result row, in order.
RESULT_COLUMNS = (
    "station_id",
    "station_name",
    "climate_zone",
    "mean_temp",
    "max_humidity",
    "total_precip",
    "n",
)

# One result row: (station_id, station_name, climate_zone,
#                  mean_temp, max_humidity, total_precip, n)
CanonicalRow = tuple[int, str, str, float, float, float, int]
CanonicalResult = list[CanonicalRow]
