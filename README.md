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

`make bench` writes `results/REPORT.md` and the two charts below. Snapshot from
one run (Apple Silicon, min of many samples — your absolute numbers will differ).

### Execution time

![Full-pipeline execution time](docs/exec_time.png)

**Full-pipeline time — min µs**

| Case | 50 | 500 | 5 000 |
|------|---:|---:|---:|
| numpy-pro | 40.4 | 94.5 | 598.4 |
| numpy-newbie | 34.2 | 225.4 | 2,201.7 |
| polars-pro | 344.5 | 377.3 | 952.5 |
| polars-newbie | 475.4 | 508.8 | 1,185.7 |
| duckdb-pro | 10,323 | 34,048 | 279,318 |
| duckdb-newbie | 51,927 | 396,469 | 3,904,522 |

**Newbie → Pro speedup (×)**

| Engine | 50 | 500 | 5 000 |
|--------|---:|---:|---:|
| polars | 1.4× | 1.3× | 1.2× |
| numpy | 0.8× | 2.4× | 3.7× |
| duckdb | 5.0× | 11.6× | 14.0× |

### Memory use

![Peak memory: import baseline vs data](docs/memory.png)

**Peak RSS — MB (`total` / `data`, where `data` = total − import baseline)**

| Case | 50 | 500 | 5 000 |
|------|---:|---:|---:|
| numpy-newbie | 81.1 / 0.3 | 80.8 / 0.0 | 81.9 / 1.1 |
| numpy-pro | 81.1 / 0.3 | 81.4 / 0.6 | 81.7 / 0.9 |
| polars-newbie | 92.9 / 11.5 | 93.2 / 11.8 | 99.7 / 18.4 |
| polars-pro | 93.0 / 12.1 | 93.5 / 12.5 | 100.1 / 19.1 |
| duckdb-newbie | 90.7 / 9.7 | 91.4 / 10.3 | 94.1 / 13.0 |
| duckdb-pro | 97.0 / 15.9 | 100.1 / 19.1 | 132.5 / 51.5 |

### What this run shows (and the caveats that matter)

- **At tiny scale, numpy wins on raw speed** — it's just in-memory arrays with no
  query-engine overhead. duckdb's absolute numbers are dominated by setup cost
  (the newbie version inserts rows one-by-one — an authentic beginner mistake).
- **"How you use it" is a real axis.** The newbie→pro speedup (up to 14× for
  duckdb here) is often larger than the gap *between* engines.
- **Memory is overhead-dominated.** The ~80 MB grey baseline (Python + numpy +
  interpreter) is essentially the same for every engine. polars and duckdb
  allocate their engine arenas/buffers on *first use*, which lands in the red
  `data` segment (12–50 MB); numpy's data footprint is ~1 MB. So numpy is the
  lightest by far, but most of the *total* is fixed cost, not the dataset
  (which is only hundreds of KB at 5 000 rows).
- **Time ≠ memory.** duckdb-**pro** is faster than duckdb-newbie yet uses *more*
  memory (single big vectorized query vs small step-by-step temp tables) — the
  two axes are independent.
- **Differences at 50–5 000 rows can be within noise.** Treat small deltas as
  indicative; the report spells out the honesty caveats.

> ⚠️ Scope note: polars vs numpy is a *query engine* vs a *numerical array
> library*. numpy wins here because the pipeline is tiny; polars is built to win
> on **large relational** workloads (joins / group-bys over millions of rows).
> For simple element-wise math, numpy can stay ahead even at large sizes. The
> 50k–millions crossover is deferred to v2.

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
