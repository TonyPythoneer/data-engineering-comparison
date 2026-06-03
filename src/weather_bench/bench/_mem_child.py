"""Child process: run one case once and report peak RSS.

Run as: ``python -m weather_bench.bench._mem_child <case> <size> <mode>``
  mode=full     -> import engine, generate data, run the pipeline, report peak RSS
  mode=baseline -> import engine only (no data work), report peak RSS

Peak RSS is captured by the OS via ``resource.getrusage`` (RUSAGE_SELF), which
counts C-level allocations that ``tracemalloc`` misses. Subprocess isolation
gives a clean high-water mark uncontaminated by anything else in the parent.
"""

from __future__ import annotations

import resource
import sys


def peak_rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports kilobytes.
    return raw if sys.platform == "darwin" else raw * 1024


def main() -> None:
    case, size, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]

    from weather_bench.common.data import generate_stations, generate_weather
    from weather_bench.engines.registry import factory_for

    # Import ONLY this case's engine (not the whole registry) so peak RSS
    # reflects this engine's standalone footprint, not all engines at once.
    # numpy is always present — the data generator uses it — so it is the
    # shared baseline every engine is measured on top of.
    pipeline = factory_for(case)()
    generate_stations()

    if mode == "full":
        from weather_bench.common.contract import run_pipeline

        stations = generate_stations()
        weather = generate_weather(size, seed=42)
        run_pipeline(pipeline, weather, stations)

    print(peak_rss_bytes())


if __name__ == "__main__":
    main()
