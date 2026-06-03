"""Registry of all engine cases, keyed by ``name``.

Built lazily so a missing optional engine import does not break the whole
registry during incremental development. The reference engine (polars-pro) is
the source of truth for golden-result equivalence.
"""

from __future__ import annotations

from collections.abc import Callable

from weather_bench.common.contract import Pipeline

# engine -> skill -> factory. Filled as cases land.
_FACTORIES: dict[str, Callable[[], Pipeline]] = {}


def _register() -> None:
    from weather_bench.engines.polars_pro import PolarsProPipeline

    _FACTORIES["polars-pro"] = PolarsProPipeline

    # Optional cases — registered if present. Keeps partial builds runnable.
    for modname, clsname, key in (
        ("polars_newbie", "PolarsNewbiePipeline", "polars-newbie"),
        ("numpy_newbie", "NumpyNewbiePipeline", "numpy-newbie"),
        ("numpy_pro", "NumpyProPipeline", "numpy-pro"),
        ("duckdb_newbie", "DuckdbNewbiePipeline", "duckdb-newbie"),
        ("duckdb_pro", "DuckdbProPipeline", "duckdb-pro"),
    ):
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


# Canonical reference for golden-result equivalence.
REFERENCE_NAME = "polars-pro"
