"""Peak-RSS memory measurement via isolated subprocesses.

Each (case, size) is measured in a *fresh* process so the peak high-water mark
is clean. We measure both:
  - total    : import engine + generate data + run pipeline
  - baseline : import engine only (fixed interpreter + library overhead)
and report ``data = max(0, total - baseline)`` as the data/compute footprint.

This path is deliberately separate from the timing path: benchmark loops would
inflate RSS, and memory profiling would distort timing.
"""

from __future__ import annotations

import subprocess
import sys

_CHILD = "weather_bench.bench._mem_child"


def _run_child(case: str, size: int, mode: str) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", _CHILD, case, str(size), mode],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(proc.stdout.strip().splitlines()[-1])


def measure_total(case: str, size: int, repeats: int = 2) -> int:
    """Peak RSS (bytes) for import + generate + run, min over ``repeats``."""
    return min(_run_child(case, size, "full") for _ in range(repeats))


def measure_baseline(case: str, repeats: int = 2) -> int:
    """Peak RSS (bytes) for import only. Size-independent, so measured once."""
    return min(_run_child(case, 0, "baseline") for _ in range(repeats))
