"""Chart generation for the benchmark report.

Writes two PNGs under ``docs/`` (committed, so they render in the README):
  - exec_time.png : full-pipeline time per case across sizes (log scale)
  - memory.png    : peak RSS at the largest size, split into import baseline
                    vs data+compute (shows that import overhead dominates)

matplotlib lives in the optional ``bench`` group; if it is missing the report
still succeeds and just skips the charts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DOCS = Path("docs")

# Stable colour per data size / segment.
_SIZE_COLORS = ("#4c72b0", "#dd8452", "#55a868")
_BASELINE_COLOR = "#bfbfbf"
_DATA_COLOR = "#d9534f"


def render_charts(
    timing: dict[tuple[str, int], dict[str, float]],
    mem: dict[tuple[str, int], dict[str, int]],
    sizes: tuple[int, ...],
    out_dir: Path = DOCS,
) -> bool:
    """Render both charts. Returns False (and warns) if matplotlib is absent."""
    try:
        import matplotlib
    except ImportError:
        print("  (matplotlib not installed — skipping charts; `uv sync --group bench`)")
        return False

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(exist_ok=True)
    cases = sorted({case for (case, _size) in timing})
    _exec_chart(plt, timing, cases, sizes, out_dir / "exec_time.png")
    _memory_chart(plt, mem, cases, sizes[-1], out_dir / "memory.png")
    print(f"  ✓ charts: {out_dir}/exec_time.png, {out_dir}/memory.png")
    return True


def _exec_chart(
    plt: Any,
    timing: dict[tuple[str, int], dict[str, float]],
    cases: list[str],
    sizes: tuple[int, ...],
    path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    n = len(sizes)
    width = 0.8 / n
    x = list(range(len(cases)))
    for i, size in enumerate(sizes):
        ys = [timing[(case, size)]["min"] * 1e6 for case in cases]  # seconds -> µs
        offsets = [xi + (i - (n - 1) / 2) * width for xi in x]
        ax.bar(offsets, ys, width=width, label=f"{size:,} rows", color=_SIZE_COLORS[i])
    ax.set_yscale("log")
    ax.set_ylabel("min time per run (µs, log scale)")
    ax.set_title("Full-pipeline execution time — lower is faster")
    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=30, ha="right")
    ax.legend(title="data size")
    ax.grid(axis="y", which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _memory_chart(
    plt: Any,
    mem: dict[tuple[str, int], dict[str, int]],
    cases: list[str],
    size: int,
    path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    x = list(range(len(cases)))
    mb = 1024 * 1024
    baseline = [mem[(case, size)]["baseline"] / mb for case in cases]
    data = [mem[(case, size)]["data"] / mb for case in cases]
    ax.bar(x, baseline, label="import baseline (fixed)", color=_BASELINE_COLOR)
    ax.bar(x, data, bottom=baseline, label="data + compute", color=_DATA_COLOR)
    ax.set_ylabel("peak RSS (MB)")
    ax.set_title(f"Peak memory at {size:,} rows — import overhead dominates")
    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
