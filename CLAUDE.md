<!-- GSD:project-start source:PROJECT.md -->

## Project

**data-engineering-comparison**

A small, reproducible benchmarking project that runs the **same weather-data pipeline** through three engines — **polars, numpy, and duckdb** — each implemented in **two skill levels** (a deliberately naive "newbie" version and an optimized "pro" version), and compares their **speed** and **memory** usage. It is a learning/comparison lab (not a production app), aimed at anyone wanting an honest, runnable side-by-side that shows both *which* tool is faster AND *how much the way you use it* matters.

**Core Value:** A single `make bench` run produces a fair, reproducible comparison table (time + memory, per engine × skill-level × operation × data size) that you can read in seconds and trust — surfacing two contrasts at once: engine-vs-engine, and newbie-vs-pro within each engine.

### Constraints

- **Tech stack**: polars, numpy, duckdb, psutil, pytest + pytest-benchmark; uv-managed; **Python 3.13** (`>=3.13,<3.14`) — polars has no cp314 wheel as of 2026-06; numpy/duckdb do. Mirror django-thumbnail tooling otherwise (ruff/pyrefly/Makefile). Revisit 3.14 when polars ships cp314.
- **Benchmark runner**: pytest-benchmark must run with `-p no:xdist` (incompatible with xdist parallel); general tests may use `-n auto` separately.
- **Memory measurement**: `resource.getrusage().ru_maxrss` in a per-case subprocess, baseline-subtracted — NOT tracemalloc (misses C allocations).
- **Performance (measurement honesty)**: At 50/500/5k rows, engine timing differences are often **sub-millisecond and may be dominated by measurement noise**. Mitigation: multi-sample benchmarks, report min/median, interpret conclusions conservatively. The linearity analysis at this range shows *trend only*, not rigorous complexity proof.
- **Memory (measurement honesty)**: At ≤5k rows the dataset is a few hundred KB — far below fixed Python/library import overhead (tens of MB). Peak RSS will likely look similar across engines, dominated by fixed cost. This outcome is itself an honest, instructive result.
- **Reproducibility**: All data is seeded; same seed → same data → comparable runs.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### Core Engines

| Package | Version | Python 3.14 cp314 Wheel | Purpose | Why |
|---------|---------|------------------------|---------|-----|
| **polars** | 1.41.2 | ✓ In development | Lazy/eager DataFrame engine | Blazingly fast, Rust-backed. Latest stable (May 29, 2026). cp314 wheels not yet on PyPI; use `pip install polars==1.41.2` and Python 3.13 as fallback OR wait for official 3.14 support. **See Blockers below.** |
| **numpy** | 2.4.6 | ✓ Yes | Numeric array operations (vectorized implementation) | Production-stable with cp314 wheels since May 18, 2026. Core for the "pro" skill level (vectorized, preallocated). |
| **duckdb** | 1.5.3 | ✓ Yes | SQL query engine with columnar storage | Production-stable with cp314 wheels since May 20, 2026. Smallest library for reproducible in-process OLAP. |

### Benchmarking & Profiling

| Package | Version | Python 3.14 Support | Purpose | Why |
|---------|---------|-------------------|---------|-----|
| **pytest-benchmark** | 5.2.3 | ✓ Yes (3.9–3.14) | Multi-sample timing with JSON export | Latest stable (Nov 9, 2025). Actively maintained; supports pytest 9.0+. Provides `benchmark` fixture, automatic calibration, JSON results, and `min`/`median` stats. **See Conflict Resolution below for xdist incompatibility.** |
| **psutil** | 7.2.2 | ✓ Yes (3.6+) | Process memory monitoring | Latest stable (Jan 28, 2026). **Peak memory measurement approach:** Use `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` for cross-platform peak RSS; psutil's standard `memory_info().rss` captures *current* RSS only. See Memory Measurement Recipe below. |

### Linting & Type Checking

| Package | Version | Purpose | Why |
|---------|---------|---------|-----|
| **ruff** | Latest | Linter (E,W,F,I,UP,B,SIM,ANN; line-length 100) | Mirrors django-thumbnail conventions; fast, all-in-one. |
| **pyright** | Latest | Static type checker | Mirrors sibling project; strict mode for type safety. |

### Testing & Development

| Package | Version | Purpose | Why |
|---------|---------|---------|-----|
| **pytest** | 8.3.x+ | Test framework | Required by pytest-benchmark; latest stable. |
| **pytest-xdist** | Latest | Parallel test runner | Required for general test speed, BUT **disabled for benchmarks** (see Conflict Resolution). |

## Installation & Dependency Groups (uv)

### pyproject.toml structure

### Installation commands

# Base + dev (includes everything except bench-only)

# Base + dev + benchmark

# Production baseline (engines only, no testing)

## Critical: Conflict Resolution (pytest-benchmark × pytest-xdist)

### The Conflict

### The Fix

# For benchmarks (correct; serial execution)

# For general tests (fast; parallel via xdist)

# To explicitly disable xdist on one run

- `-p no:xdist` unloads the xdist plugin entirely, preventing parallel execution.
- `make bench` uses clean pytest invocation without xdist flags.
- General test suite can still use `-n auto` when run separately.

## Memory Measurement Recipe

### Why NOT tracemalloc

### Recommended Approach: `resource.getrusage()`

- `ru_maxrss` is the kernel's **peak** (max) RSS measurement, not current.
- Captures C allocations (unlike tracemalloc).
- Available on Unix (Linux, macOS, BSD); Windows support via `psutil.Process().memory_info().peak_wset` if needed.
- Cross-platform with unit normalization.

### Alternative: psutil + Sampling (less reliable)

### Implementation in Fixture

# conftest.py

## pytest-benchmark API Quick Reference

### Basic Usage

### Access Statistics

### JSON Export

# Writes .benchmarks/*/Linux-...-result.json

### Comparison Mode

# Compares against previously saved `baseline` run

## Wheel Availability Status (HIGH confidence)

| Package | Version | cp314 Wheels | Release Date | Notes |
|---------|---------|-------------|----------------|--------|
| polars | 1.41.2 | ⚠️ **No** (in development) | May 29, 2026 | Official cp314 support pending. Third-party wheels exist ([harshil21/polars-runtime-32-ft](https://github.com/harshil21/polars-runtime-32-ft)) but not on PyPI. **Recommendation: Pin Python 3.13 for now** or monitor [polars/pypi](https://pypi.org/project/polars/) for cp314 wheels. |
| numpy | 2.4.6 | ✓ Yes | May 18, 2026 | All platforms (macOS, Linux, Windows). Ready for Python 3.14. |
| duckdb | 1.5.3 | ✓ Yes | May 20, 2026 | All platforms; free-threading (t) wheels planned. Ready for Python 3.14. |
| pytest-benchmark | 5.2.3 | ✓ Yes | Nov 9, 2025 | Supports Python 3.9–3.14. Production-stable. |
| psutil | 7.2.2 | ✓ Yes | Jan 28, 2026 | Supports Python 3.6+. Latest enhancements for Linux pidfd_open and macOS kqueue. |

## Blockers & Workarounds

### 1. Polars Python 3.14 Wheels Not Yet Available (Jan 2026 → May 2026 status)

### 2. Memory Measurement on Windows

## Source Dependencies

- [polars PyPI (1.41.2)](https://pypi.org/project/polars/)
- [numpy PyPI (2.4.6)](https://pypi.org/project/numpy/)
- [duckdb PyPI (1.5.3)](https://pypi.org/project/duckdb/)
- [pytest-benchmark PyPI (5.2.3)](https://pypi.org/project/pytest-benchmark/)
- [psutil PyPI (7.2.2)](https://psutil.readthedocs.io/)
- [pytest-xdist documentation](https://pytest-xdist.readthedocs.io/en/latest/)
- [uv dependency-groups](https://docs.astral.sh/uv/concepts/projects/dependencies/)
- [Python 3.14 wheels readiness](https://status.fedoralovespython.org/wheels_py314/)

## Confidence Levels

| Area | Confidence | Reason |
|------|------------|--------|
| **Core engine versions** | HIGH | Verified against PyPI as of June 3, 2026. All except polars have cp314 wheels. |
| **pytest-benchmark compatibility & API** | HIGH | Version 5.2.3 supports Python 3.9–3.14; documentation current (Nov 2025). |
| **pytest-benchmark × xdist conflict resolution** | HIGH | Standard practice documented in pytest-xdist; `-p no:xdist` is the canonical workaround. |
| **Memory measurement approach** | HIGH | `resource.getrusage().ru_maxrss` is the standard Unix method; psutil docstring confirms it's the way to capture peak RSS incl. C allocations. |
| **Polars Python 3.14 wheels** | MEDIUM | Status is "in development"; third-party wheels exist; official wheels expected within 1–2 quarters. Recommend Python 3.13 fallback. |
| **uv dependency-groups syntax** | HIGH | Verified against uv docs (PEP 735). Syntax is stable as of 2026. |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
