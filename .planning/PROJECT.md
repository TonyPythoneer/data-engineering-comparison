# data-engineering-comparison

## What This Is

A small, reproducible benchmarking project that runs the **same weather-data pipeline** through three engines — **polars, numpy, and duckdb** — and compares their **speed** and **memory** usage. It is a learning/comparison lab (not a production app), aimed at anyone wanting an honest, runnable side-by-side of these three tools on a friendly, easy-to-understand dataset.

## Core Value

A single `make bench` run produces a fair, reproducible comparison table (time + memory, per engine, per operation, across data sizes) that you can read in seconds and trust.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Seeded synthetic **weather dataset generator** (columns: station_id, date, temperature, humidity, precipitation, wind_speed), scalable to a requested row count, fully reproducible, no download
- [ ] Same 5-step **pipeline** implemented per engine: load → filter → groupby-aggregate → join → sort
- [ ] **polars** implementation of the pipeline
- [ ] **numpy** implementation of the pipeline (groupby/join hand-rolled — the ergonomics gap is part of the comparison)
- [ ] **duckdb** implementation of the pipeline
- [ ] **Time** measurement via `pytest-benchmark` (multi-sample, report min/median to suppress noise)
- [ ] **Memory** measurement via peak process RSS using `psutil` (NOT tracemalloc — C-level allocations would be undercounted)
- [ ] Run across **data sizes 50 / 500 / 5k** rows
- [ ] **Scaling / linearity analysis** across the three sizes — check whether performance degrades as data grows
- [ ] **Markdown comparison report** (README-pasteable: time + memory, per engine × operation × size)
- [ ] `make bench` one-shot target that runs everything and produces the report
- [ ] Mirror sibling project conventions: uv deps + `[dependency-groups]` dev, pytest, ruff, pyrefly, Makefile (test/check/fix/bench), Python 3.14, README

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Docker / Celery / database / web layer — this is a pure benchmarking lib, not a web app (sibling django-thumbnail had these; we deliberately drop them)
- Pandas and other engines — scope is exactly the three requested (polars, numpy, duckdb); adding more dilutes the comparison
- Large-scale / big-data datasets — deliberately small (≤5k rows) for understandability and fast runs; honest tradeoff is that small sizes make differences subtle (see Constraints)
- Real downloaded weather data (NOAA/Open-Meteo) — synthetic chosen for reproducibility and zero-download

## Context

- **Sibling reference project**: `../django-thumbnail` provides the stack conventions to mirror — `uv` with `[dependency-groups]` dev, `pytest` (+ `pytest-xdist`), `ruff` (select `E,W,F,I,UP,B,SIM,ANN`, `line-length=100`), `pyrefly` for types, a `Makefile` with `test`/`check`/`fix` targets, Python `3.14`, README.
- **Repo already exists**: github.com/TonyPythoneer/data-engineering-comparison, local dir `/Users/tonyyang/git/personal/data-engineering-comparision` (note: local dir name keeps the old `comparision` spelling; remote is `comparison`).
- **numpy ergonomics note**: numpy has no native groupby/join, so those steps are hand-rolled. This is intentional — the comparison is speed *and* developer ergonomics.

## Constraints

- **Tech stack**: polars, numpy, duckdb, psutil, pytest + pytest-benchmark; uv-managed; Python 3.14 — mirror django-thumbnail tooling for consistency across the user's projects.
- **Performance (measurement honesty)**: At 50/500/5k rows, engine timing differences are often **sub-millisecond and may be dominated by measurement noise**. Mitigation: multi-sample benchmarks, report min/median, interpret conclusions conservatively. The linearity analysis at this range shows *trend only*, not rigorous complexity proof.
- **Memory (measurement honesty)**: At ≤5k rows the dataset is a few hundred KB — far below fixed Python/library import overhead (tens of MB). Peak RSS will likely look similar across engines, dominated by fixed cost. This outcome is itself an honest, instructive result.
- **Reproducibility**: All data is seeded; same seed → same data → comparable runs.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Compare exactly polars / numpy / duckdb | User's explicit scope | — Pending |
| Synthetic seeded weather data | Reproducible, friendly to understand, zero-download | — Pending |
| Data sizes 50 / 500 / 5k | Keep it small and easy; concept-first over magnitude of difference | — Pending |
| Add scaling/linearity analysis | User wants to see if perf drops as size grows | — Pending |
| Time via pytest-benchmark, memory via psutil peak RSS | Statistical timing; RSS captures C-level allocations tracemalloc misses | — Pending |
| numpy groupby/join hand-rolled | numpy has no native primitives; ergonomics gap is part of the comparison | — Pending |
| Markdown report + `make bench` entry point | README-pasteable, mirrors django-thumbnail Makefile convention | — Pending |
| Drop Docker/Celery/DB | Pure benchmarking lib, not a web app | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-03 after initialization*
