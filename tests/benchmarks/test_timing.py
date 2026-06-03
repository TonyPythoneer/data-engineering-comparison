"""Headline timing via pytest-benchmark: full pipeline per (case, size).

Run on its own to produce the timing JSON the report consumes:

    uv run -m pytest tests/benchmarks --benchmark-json=results/timing.json -p no:xdist

These are marked ``benchmark`` and excluded from the default ``make test`` run
(addopts: -m "not benchmark") so the correctness suite stays fast.
"""

import pytest

from weather_bench.common.contract import run_pipeline
from weather_bench.common.data import generate_stations, generate_weather
from weather_bench.engines.registry import all_pipelines, get_pipeline

CASES = sorted(all_pipelines())
SIZES = (50, 500, 5000)


@pytest.mark.benchmark
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("case", CASES)
def test_pipeline(benchmark, case, size):
    stations = generate_stations()
    weather = generate_weather(size, seed=42)
    benchmark.group = f"size={size}"
    benchmark.extra_info["case"] = case
    benchmark.extra_info["size"] = size
    result = benchmark(lambda: run_pipeline(get_pipeline(case), weather, stations))
    assert result  # pipeline produced rows
