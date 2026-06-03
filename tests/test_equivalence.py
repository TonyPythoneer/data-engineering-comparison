"""The equivalence gate: every engine case must produce byte-identical output.

This is a HARD gate. Benchmark numbers are only meaningful if all six cases
compute exactly the same result on the same seeded data. If this fails, the
comparison is invalid — fix the engine before trusting any timing.
"""

import pytest

from weather_bench.common.contract import run_pipeline
from weather_bench.common.data import generate_stations, generate_weather
from weather_bench.engines.registry import REFERENCE_NAME, all_pipelines

SIZES = (50, 500, 5000)
CASES = sorted(all_pipelines())


def test_all_cases_registered():
    expected = {
        "polars-newbie",
        "polars-pro",
        "numpy-newbie",
        "numpy-pro",
        "duckdb-newbie",
        "duckdb-pro",
        "pandas-newbie",
        "pandas-pro",
    }
    assert set(CASES) == expected


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("case", CASES)
def test_case_matches_reference(case, size):
    stations = generate_stations()
    weather = generate_weather(size, seed=42)
    reference = run_pipeline(all_pipelines()[REFERENCE_NAME], weather, stations)
    result = run_pipeline(all_pipelines()[case], weather, stations)
    assert result == reference, f"{case} diverges from {REFERENCE_NAME} at size={size}"


@pytest.mark.parametrize("size", SIZES)
def test_result_is_sorted_by_total_precip_desc(size):
    stations = generate_stations()
    weather = generate_weather(size, seed=42)
    result = run_pipeline(all_pipelines()[REFERENCE_NAME], weather, stations)
    prec = [row[5] for row in result]
    assert prec == sorted(prec, reverse=True)
