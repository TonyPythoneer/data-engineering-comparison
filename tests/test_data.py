"""Data generator: reproducibility and shape."""

from weather_bench.common.data import N_STATIONS, generate_stations, generate_weather
from weather_bench.common.schema import STATION_COLUMNS, WEATHER_COLUMNS


def test_weather_is_reproducible():
    a = generate_weather(500, seed=42)
    b = generate_weather(500, seed=42)
    assert a == b


def test_weather_seed_changes_data():
    a = generate_weather(500, seed=1)
    b = generate_weather(500, seed=2)
    assert a != b


def test_weather_shape():
    w = generate_weather(123)
    assert set(w) == set(WEATHER_COLUMNS)
    assert all(len(col) == 123 for col in w.values())
    assert all(0 <= sid < N_STATIONS for sid in w["station_id"])


def test_stations_shape():
    s = generate_stations()
    assert set(s) == set(STATION_COLUMNS)
    assert all(len(col) == N_STATIONS for col in s.values())
    assert s["station_id"] == list(range(N_STATIONS))
