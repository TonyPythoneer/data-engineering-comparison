"""duckdb - NEWBIE: step-by-step materialized temp tables + repeated scans.

Authentic beginner pattern: after each logical step, materialize a new temp
table via CREATE TABLE ... AS SELECT *. State tracks the DuckDB connection
and the latest temp-table name. Each step scans and rebuilds. This shows the
cost of repeated evaluation and materialization overhead that naive usage incurs.
"""

from __future__ import annotations

import duckdb

from weather_bench.common.contract import normalize
from weather_bench.common.schema import (
    FILTER_HUMIDITY_MAX,
    FILTER_TEMP_MIN,
    CanonicalResult,
    RawTable,
)


class DuckdbNewbiePipeline:
    name = "duckdb-newbie"

    def load(self, weather: RawTable, stations: RawTable) -> tuple[duckdb.DuckDBPyConnection, str]:
        """Load weather and stations into DuckDB, register as tables.

        Returns the connection and the name of the current weather table.
        """
        con = duckdb.connect(":memory:")

        # Create and populate weather table from dict columns.
        weather_cols = ", ".join(
            f"{k} DOUBLE"
            if k in ("temperature", "humidity", "precipitation", "wind_speed")
            else f"{k} INTEGER"
            for k in weather
        )
        con.execute(f"CREATE TABLE weather ({weather_cols})")

        # Insert weather data.
        for i in range(len(next(iter(weather.values())))):
            values = [weather[col][i] for col in weather]
            placeholders = ", ".join(["?"] * len(values))
            con.execute(f"INSERT INTO weather VALUES ({placeholders})", values)

        # Create and populate stations table from dict columns.
        stations_cols = ", ".join(
            f"{k} DOUBLE"
            if k in ("latitude", "longitude", "elevation_m")
            else f"{k} VARCHAR"
            if k in ("station_name", "climate_zone")
            else f"{k} INTEGER"
            for k in stations
        )
        con.execute(f"CREATE TABLE stations ({stations_cols})")

        # Insert stations data.
        for i in range(len(next(iter(stations.values())))):
            values = [stations[col][i] for col in stations]
            placeholders = ", ".join(["?"] * len(values))
            con.execute(f"INSERT INTO stations VALUES ({placeholders})", values)

        return con, "weather"

    def filter(
        self, state: tuple[duckdb.DuckDBPyConnection, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str]:
        """Filter weather table; materialize as weather_filtered temp table."""
        con, weather_tbl = state

        con.execute(
            f"""
            CREATE TEMP TABLE weather_filtered AS
            SELECT * FROM {weather_tbl}
            WHERE temperature > {FILTER_TEMP_MIN}
              AND humidity < {FILTER_HUMIDITY_MAX}
            """
        )

        return con, "weather_filtered"

    def aggregate(
        self, state: tuple[duckdb.DuckDBPyConnection, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str]:
        """Aggregate by station_id; materialize as weather_agg temp table."""
        con, weather_tbl = state

        con.execute(
            f"""
            CREATE TEMP TABLE weather_agg AS
            SELECT
                station_id,
                AVG(temperature) AS mean_temp,
                MAX(humidity) AS max_humidity,
                SUM(precipitation) AS total_precip,
                COUNT(*) AS n
            FROM {weather_tbl}
            GROUP BY station_id
            """
        )

        return con, "weather_agg"

    def join(
        self, state: tuple[duckdb.DuckDBPyConnection, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str]:
        """Join aggregated weather with stations; materialize as weather_joined."""
        con, agg_tbl = state

        con.execute(
            f"""
            CREATE TEMP TABLE weather_joined AS
            SELECT
                a.station_id,
                s.station_name,
                s.climate_zone,
                a.mean_temp,
                a.max_humidity,
                a.total_precip,
                a.n
            FROM {agg_tbl} a
            INNER JOIN stations s ON a.station_id = s.station_id
            """
        )

        return con, "weather_joined"

    def sort(
        self, state: tuple[duckdb.DuckDBPyConnection, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str]:
        """Sort by total_precip DESC, station_id ASC; materialize as weather_sorted."""
        con, joined_tbl = state

        con.execute(
            f"""
            CREATE TEMP TABLE weather_sorted AS
            SELECT * FROM {joined_tbl}
            ORDER BY total_precip DESC, station_id ASC
            """
        )

        return con, "weather_sorted"

    def materialize(self, state: tuple[duckdb.DuckDBPyConnection, str]) -> CanonicalResult:
        """Fetch all rows from the final sorted table and normalize."""
        con, sorted_tbl = state

        result = con.execute(f"SELECT * FROM {sorted_tbl}").fetchall()

        rows = [
            (
                int(row[0]),
                str(row[1]),
                str(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5]),
                int(row[6]),
            )
            for row in result
        ]

        return normalize(rows)
