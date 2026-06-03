"""`make bench` entry point: run all measurements and write the Markdown report.

Pipeline of work:
  1. Run the equivalence gate — abort if any case diverges (numbers would lie).
  2. Run pytest-benchmark (serial) -> results/timing.json — headline full-pipeline timing.
  3. Measure peak RSS per case/size in isolated subprocesses (baseline-subtracted).
  4. Measure the in-process per-operation breakdown at the largest size.
  5. Fit a linear scaling model (fixed + marginal cost) per case.
  6. Emit results/REPORT.md (README-pasteable) with honesty caveats.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from weather_bench.bench import memory
from weather_bench.bench.timing import ROUNDS_BY_SIZE, time_steps
from weather_bench.common.data import generate_stations, generate_weather
from weather_bench.common.schema import STEP_NAMES
from weather_bench.engines.registry import all_pipelines, get_pipeline

SIZES = (50, 500, 5000)
ENGINES = ("polars", "numpy", "duckdb")
RESULTS_DIR = Path("results")
TIMING_JSON = RESULTS_DIR / "timing.json"
REPORT_MD = RESULTS_DIR / "REPORT.md"


# --------------------------------------------------------------------------- #
# Steps
# --------------------------------------------------------------------------- #
def _run_equivalence_gate() -> None:
    print("→ equivalence gate ...", flush=True)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_equivalence.py", "-q", "-p", "no:xdist"],
    )
    if proc.returncode != 0:
        sys.exit("✗ equivalence gate FAILED — engines diverge; benchmark aborted.")
    print("  ✓ all cases identical\n", flush=True)


def _run_pytest_benchmark() -> dict[tuple[str, int], dict[str, float]]:
    print("→ timing via pytest-benchmark ...", flush=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/benchmarks",
            "-m",
            "benchmark",  # override the default '-m not benchmark' addopts
            "--benchmark-only",
            f"--benchmark-json={TIMING_JSON}",
            "-q",
            "-p",
            "no:xdist",
        ],
        check=True,
    )
    data = json.loads(TIMING_JSON.read_text())
    out: dict[tuple[str, int], dict[str, float]] = {}
    for bench in data["benchmarks"]:
        info = bench.get("extra_info", {})
        case = info["case"]
        size = int(info["size"])
        stats = bench["stats"]
        out[(case, size)] = {"min": stats["min"], "median": stats["median"]}
    print(f"  ✓ {len(out)} (case,size) timings\n", flush=True)
    return out


def _measure_memory() -> dict[tuple[str, int], dict[str, int]]:
    print("→ peak RSS in isolated subprocesses ...", flush=True)
    cases = sorted(all_pipelines())
    out: dict[tuple[str, int], dict[str, int]] = {}
    for case in cases:
        baseline = memory.measure_baseline(case)
        for size in SIZES:
            total = memory.measure_total(case, size)
            out[(case, size)] = {
                "total": total,
                "baseline": baseline,
                "data": max(0, total - baseline),
            }
        print(f"  ✓ {case}", flush=True)
    print(flush=True)
    return out


def _measure_per_op(size: int) -> dict[str, dict[str, dict[str, float]]]:
    print(f"→ per-operation breakdown (in-process, size={size}) ...", flush=True)
    stations = generate_stations()
    weather = generate_weather(size, seed=42)
    rounds = ROUNDS_BY_SIZE[size]
    out: dict[str, dict[str, dict[str, float]]] = {}
    for case in sorted(all_pipelines()):
        out[case] = time_steps(lambda c=case: get_pipeline(c), weather, stations, rounds)
    print("  ✓ done\n", flush=True)
    return out


def _linfit(xs: list[int], ys: list[float]) -> tuple[float, float]:
    """Least-squares fit y = a + b*x. Returns (a, b)."""
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
    denom = n * sxx - sx * sx
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    return a, b


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def _us(seconds: float) -> str:
    return f"{seconds * 1e6:,.1f}"


def _mb(num_bytes: int) -> str:
    return f"{num_bytes / 1024 / 1024:.1f}"


def _case(engine: str, skill: str) -> str:
    return f"{engine}-{skill}"


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def _build_markdown(
    timing: dict[tuple[str, int], dict[str, float]],
    mem: dict[tuple[str, int], dict[str, int]],
    per_op: dict[str, dict[str, dict[str, float]]],
    per_op_size: int,
) -> str:
    cases = sorted({case for (case, _size) in timing})
    lines: list[str] = []
    a = lines.append

    a("# Benchmark Report — polars vs numpy vs duckdb\n")
    a("Same 5-step weather pipeline (load → filter → groupby-agg → join → sort),")
    a("each engine in a **newbie** (naive) and **pro** (optimized) version.")
    a("All six cases produce byte-identical output (equivalence gate passed).\n")

    # --- 1. Headline timing -------------------------------------------------
    a("## 1. Full-pipeline time — min µs (pytest-benchmark)\n")
    a("| Case | " + " | ".join(f"{s} rows" for s in SIZES) + " |")
    a("|------|" + "|".join("---:" for _ in SIZES) + "|")
    for case in cases:
        cells = [_us(timing[(case, s)]["min"]) for s in SIZES]
        a(f"| {case} | " + " | ".join(cells) + " |")
    a("")

    # --- 2. Newbie -> Pro speedup ------------------------------------------
    a("## 2. Newbie → Pro speedup (×, higher = pro is faster)\n")
    a("| Engine | " + " | ".join(f"{s} rows" for s in SIZES) + " |")
    a("|--------|" + "|".join("---:" for _ in SIZES) + "|")
    for engine in ENGINES:
        cells = []
        for s in SIZES:
            nb = timing[(_case(engine, "newbie"), s)]["min"]
            pro = timing[(_case(engine, "pro"), s)]["min"]
            cells.append(f"{nb / pro:.1f}×")
        a(f"| {engine} | " + " | ".join(cells) + " |")
    a("")

    # --- 3. Per-operation breakdown ----------------------------------------
    a(f"## 3. Per-operation time — min µs (in-process, size={per_op_size})\n")
    a("Lazy engines (polars-pro, duckdb-pro) defer work to **materialize** —")
    a("their transform steps read ~0 and the cost lands at the end. That is the point.\n")
    a("| Case | " + " | ".join(STEP_NAMES) + " |")
    a("|------|" + "|".join("---:" for _ in STEP_NAMES) + "|")
    for case in cases:
        cells = [_us(per_op[case][step]["min"]) for step in STEP_NAMES]
        a(f"| {case} | " + " | ".join(cells) + " |")
    a("")

    # --- 4. Memory ----------------------------------------------------------
    a("## 4. Peak memory — MB (isolated subprocess, RSS)\n")
    a("`total` = interpreter + library import + data + compute.")
    a("`data` = total − baseline (import-only), i.e. the marginal footprint of the work.\n")
    a("| Case | " + " | ".join(f"{s} total / data" for s in SIZES) + " |")
    a("|------|" + "|".join("---:" for _ in SIZES) + "|")
    for case in cases:
        cells = [f"{_mb(mem[(case, s)]['total'])} / {_mb(mem[(case, s)]['data'])}" for s in SIZES]
        a(f"| {case} | " + " | ".join(cells) + " |")
    a("")

    # --- 5. Scaling ---------------------------------------------------------
    a("## 5. Scaling fit — time ≈ fixed + marginal × rows\n")
    a("Linear least-squares on 3 points. **Trend only** — 3 points cannot prove")
    a("algorithmic complexity; treat the marginal term as indicative.\n")
    a("| Case | fixed (µs) | marginal (µs/1k rows) |")
    a("|------|-----------:|----------------------:|")
    for case in cases:
        ys = [timing[(case, s)]["min"] for s in SIZES]
        fixed, marginal = _linfit(list(SIZES), ys)
        a(f"| {case} | {fixed * 1e6:,.1f} | {marginal * 1e9:,.2f} |")
    a("")

    # --- Caveats ------------------------------------------------------------
    a("## Measurement honesty\n")
    a("- **Tiny data (50–5k rows).** Many timings are sub-millisecond; differences")
    a("  can be within jitter. We report the **min** of many samples (most robust).")
    a("- **Memory is overhead-dominated.** Import overhead (tens of MB) dwarfs a")
    a("  few-hundred-KB dataset, so `data` deltas are small and noisy — the honest")
    a("  result is that fixed cost dominates at this scale.")
    a("- **Lazy attribution.** polars-pro / duckdb-pro concentrate cost in")
    a("  `materialize`; per-op rows are ~0 by design, not by error.")
    a("- **Reproducible.** Seeded data; same seed → same numbers (modulo machine noise).")
    a("")
    return "\n".join(lines)


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    _run_equivalence_gate()
    timing = _run_pytest_benchmark()
    mem = _measure_memory()
    per_op_size = SIZES[-1]
    per_op = _measure_per_op(per_op_size)

    markdown = _build_markdown(timing, mem, per_op, per_op_size)
    REPORT_MD.write_text(markdown)
    print(f"✓ report written: {REPORT_MD}\n")
    print(markdown)


if __name__ == "__main__":
    main()
