.PHONY: sync test check fix bench equiv clean help

# ============================================================
# Config
# ============================================================
# The user's shell sets UV_PYTHON globally; pin to 3.13 here so every target
# uses the project interpreter (polars has no cp314 wheels yet).
export UV_PYTHON = 3.13
UV = uv run

# ============================================================
# Setup
# ============================================================
sync:               ## Install all dependency groups (dev + bench)
	uv sync --group dev --group bench

# ============================================================
# Code quality
# ============================================================
test:               ## Run the pytest suite (correctness + equivalence)
	$(UV) -m pytest

check:              ## Verify lint + format + types (read-only, CI-safe)
	$(UV) -m ruff check
	$(UV) -m ruff format --check
	$(UV) -m pyrefly check

fix:                ## Auto-fix lint + format
	$(UV) -m ruff check --fix
	$(UV) -m ruff format

equiv:              ## Run only the cross-engine equivalence gate
	$(UV) -m pytest tests/test_equivalence.py -v

# ============================================================
# Benchmark (the headline deliverable)
# ============================================================
bench:              ## Run all benchmarks (time + memory) and write the Markdown report
	$(UV) -m weather_bench.report.generate

# ============================================================
# Cleanup
# ============================================================
clean:              ## Remove caches and generated artifacts
	rm -rf .pytest_cache .ruff_cache .benchmarks results
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

# ============================================================
# Help
# ============================================================
help:               ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
