# data-engineering-comparison

A small, reproducible **micro-benchmark** that runs the *same* 5-step weather
pipeline through three engines — **polars**, **numpy**, **duckdb** — each written
twice: a **newbie** (naive) version and a **pro** (optimized) version. It measures
**time** and **peak memory**, and reports both *which engine* is faster and
*how much the way you use it* matters.

> 6 cases = 3 engines × {newbie, pro}. All six produce **byte-identical** output
> (enforced by an equivalence gate) so the comparison is fair.

## The pipeline

Identical semantics across all six cases, on a seeded synthetic weather dataset
(`station_id, date, temperature, humidity, precipitation, wind_speed`) joined to a
small station dimension:

1. **load** → 2. **filter** (`temperature > 20 AND humidity < 80`) →
3. **groupby-aggregate** (per station: mean temp, max humidity, total precip, count) →
4. **join** (station name + climate zone) → 5. **sort** (total precip desc)

Data sizes: **50 / 500 / 5 000** rows.

## Quick start

```bash
make sync     # install deps (uv, Python 3.13)
make test     # correctness + cross-engine equivalence gate
make bench    # run all benchmarks and write results/REPORT.md
make check    # ruff + format + pyrefly
make fix      # auto-fix lint/format
```

## How it works (honest measurement)

- **Time** — `pytest-benchmark` (serial, `-p no:xdist`) for the headline
  full-pipeline number; an in-process per-op breakdown for the step view.
- **Memory** — peak RSS via `resource.getrusage` in an **isolated subprocess**
  per case, with the import-only **baseline subtracted** to expose the data-only
  footprint. (`tracemalloc` is *not* used — it misses C-level allocations.)
- Timing and memory run as **separate paths** (benchmark loops would inflate RSS).
- **Python 3.13** is pinned: polars has no cp314 wheel yet.

### Reading the report

`make bench` writes `results/REPORT.md`. Snapshot from one run (Apple Silicon,
min of many samples — your absolute numbers will differ):

**Full-pipeline time — min µs**

| Case | 50 | 500 | 5 000 |
|------|---:|---:|---:|
| numpy-pro | 40.5 | 94.6 | 600.0 |
| numpy-newbie | 34.3 | 226.7 | 2,211.2 |
| polars-pro | 337.5 | 372.9 | 957.3 |
| polars-newbie | 497.1 | 516.2 | 1,142.3 |
| duckdb-pro | 10,315 | 33,189 | 273,092 |
| duckdb-newbie | 51,398 | 421,662 | 3,821,697 |

**Newbie → Pro speedup (×)**

| Engine | 50 | 500 | 5 000 |
|--------|---:|---:|---:|
| polars | 1.5× | 1.4× | 1.2× |
| numpy | 0.8× | 2.4× | 3.7× |
| duckdb | 5.0× | 12.7× | 14.0× |

What this particular run shows (and the caveats that matter):

- **At tiny scale, numpy wins on raw speed** — it's just in-memory arrays with no
  query engine overhead. duckdb's absolute numbers are dominated by setup cost
  (the newbie version inserts rows one-by-one — an authentic beginner mistake).
- **"How you use it" is a real axis.** The newbie→pro speedup (up to 14× for
  duckdb here) is often larger than the gap *between* engines.
- **Differences at 50–5 000 rows can be within noise**, and **memory is dominated
  by fixed import overhead** (tens of MB) — the dataset is only hundreds of KB.
  The report states these caveats explicitly; treat small deltas as indicative.

## Project layout

```
src/weather_bench/
  common/   schema.py · data.py (seeded generator) · contract.py (PipelineProtocol)
  engines/  polars_{newbie,pro}.py · numpy_{newbie,pro}.py · duckdb_{newbie,pro}.py · registry.py
  bench/    timing.py (per-op) · memory.py + _mem_child.py (subprocess RSS)
  report/   generate.py  (make bench entry point)
tests/      test_data.py · test_equivalence.py · benchmarks/test_timing.py
```

Built with [GSD](https://github.com/) planning: see `.planning/` (local-only).
