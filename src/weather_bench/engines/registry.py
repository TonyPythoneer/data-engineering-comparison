"""Registry of all engine cases, keyed by ``name``.

``CASE_SPECS`` is a plain ``(module, class, key)`` table — importing it does NOT
import any engine library, so the memory subprocess can import just the one
engine it measures (see ``bench._mem_child``). Factories are built lazily so a
missing optional engine import does not break the whole registry.
"""

from __future__ import annotations

from collections.abc import Callable

from weather_bench.common.contract import Pipeline

# (module name, class name, registry key). Order here is incidental; display
# order lives in schema.case_sort_key. polars-pro is the equivalence reference.
CASE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("polars_pro", "PolarsProPipeline", "polars-pro"),
    ("polars_newbie", "PolarsNewbiePipeline", "polars-newbie"),
    ("numpy_newbie", "NumpyNewbiePipeline", "numpy-newbie"),
    ("numpy_pro", "NumpyProPipeline", "numpy-pro"),
    ("duckdb_newbie", "DuckdbNewbiePipeline", "duckdb-newbie"),
    ("duckdb_pro", "DuckdbProPipeline", "duckdb-pro"),
    ("pandas_newbie", "PandasNewbiePipeline", "pandas-newbie"),
    ("pandas_pro", "PandasProPipeline", "pandas-pro"),
)

# Canonical reference for golden-result equivalence.
REFERENCE_NAME = "polars-pro"

_FACTORIES: dict[str, Callable[[], Pipeline]] = {}


def factory_for(key: str) -> Callable[[], Pipeline]:
    """Import and return the factory for a single case (only that engine's lib)."""
    for modname, clsname, spec_key in CASE_SPECS:
        if spec_key == key:
            module = __import__(f"weather_bench.engines.{modname}", fromlist=[clsname])
            return getattr(module, clsname)
    raise KeyError(key)


def _register() -> None:
    for modname, clsname, key in CASE_SPECS:
        try:
            module = __import__(f"weather_bench.engines.{modname}", fromlist=[clsname])
            _FACTORIES[key] = getattr(module, clsname)
        except ImportError:
            continue


def all_pipelines() -> dict[str, Pipeline]:
    """Instantiate every registered engine case."""
    if not _FACTORIES:
        _register()
    return {name: factory() for name, factory in _FACTORIES.items()}


def get_pipeline(name: str) -> Pipeline:
    if not _FACTORIES:
        _register()
    return _FACTORIES[name]()
