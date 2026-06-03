"""duckdb - PRO: a single lazy relation chain; the query optimizer fuses the steps.

Reference implementation for DuckDB. Each transform step only extends a
``Relation`` plan (near-zero cost); all real work happens in ``materialize``
at ``.fetchall()``. That is the point of the Relation API and shows up in
the per-op timing. Uses SQL strings built iteratively to compose the query.
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


class DuckdbProPipeline:
    name = "duckdb-pro"

    def load(
        self, weather: RawTable, stations: RawTable
    ) -> tuple[duckdb.DuckDBPyConnection, str, str]:
        con = duckdb.connect()
        weather_rel = self._dict_to_relation(con, weather)
        stations_rel = self._dict_to_relation(con, stations)
        weather_rel.to_view("_weather")
        stations_rel.to_view("_stations")
        return con, "_weather", "_stations"

    @staticmethod
    def _dict_to_relation(
        con: duckdb.DuckDBPyConnection, data: RawTable
    ) -> duckdb.DuckDBPyRelation:
        """Convert a columnar dict to a DuckDB Relation via VALUES clause."""
        keys = list(data.keys())
        n_rows = len(data[keys[0]])
        rows = []
        for i in range(n_rows):
            vals = tuple(data[k][i] for k in keys)
            rows.append(vals)
        col_names = ", ".join(keys)
        values_str = ", ".join(str(row) for row in rows)
        return con.sql(f"SELECT * FROM (VALUES {values_str}) AS t({col_names})")

    def filter(
        self, state: tuple[duckdb.DuckDBPyConnection, str, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str, str]:
        con, weather_tbl, stations_tbl = state
        query = f"""
            SELECT * FROM {weather_tbl}
            WHERE temperature > {FILTER_TEMP_MIN}
              AND humidity < {FILTER_HUMIDITY_MAX}
        """
        con.sql(query).to_view("_weather_filtered")
        return con, "_weather_filtered", stations_tbl

    def aggregate(
        self, state: tuple[duckdb.DuckDBPyConnection, str, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str, str]:
        con, weather_tbl, stations_tbl = state
        query = f"""
            SELECT
                station_id,
                AVG(temperature) AS mean_temp,
                MAX(humidity) AS max_humidity,
                SUM(precipitation) AS total_precip,
                COUNT(*) AS n
            FROM {weather_tbl}
            GROUP BY station_id
        """
        con.sql(query).to_view("_weather_agg")
        return con, "_weather_agg", stations_tbl

    def join(
        self, state: tuple[duckdb.DuckDBPyConnection, str, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str]:
        con, weather_tbl, stations_tbl = state
        query = f"""
            SELECT
                w.station_id,
                s.station_name,
                s.climate_zone,
                w.mean_temp,
                w.max_humidity,
                w.total_precip,
                w.n
            FROM {weather_tbl} w
            INNER JOIN {stations_tbl} s ON w.station_id = s.station_id
        """
        con.sql(query).to_view("_weather_joined")
        return con, "_weather_joined"

    def sort(
        self, state: tuple[duckdb.DuckDBPyConnection, str]
    ) -> tuple[duckdb.DuckDBPyConnection, str]:
        con, weather_tbl = state
        query = f"""
            SELECT * FROM {weather_tbl}
            ORDER BY total_precip DESC, station_id ASC
        """
        con.sql(query).to_view("_weather_sorted")
        return con, "_weather_sorted"

    def materialize(self, state: tuple[duckdb.DuckDBPyConnection, str]) -> CanonicalResult:
        con, weather_tbl = state
        rows = [tuple(r) for r in con.sql(f"SELECT * FROM {weather_tbl}").fetchall()]
        return normalize(rows)
