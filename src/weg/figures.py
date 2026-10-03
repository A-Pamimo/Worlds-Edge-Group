"""Shared figure styling and deterministic SVG/PNG export.

Rules from the brief: minimal styling, primary colour #1B2A41, no titles baked in.
Palette note: the brand navy is darker and lower-chroma than a general categorical
palette validator would accept for multi-series charts. We therefore design charts
around ONE primary series in navy, use the gold highlight for the single entity the
chart is about (usually China) and greys for context series, and always add direct
labels when more than one series is drawn, so identity never rests on colour alone.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PRIMARY = "#1B2A41"
HIGHLIGHT = "#B88800"
GREY_DARK = "#7A8699"
GREY_LIGHT = "#C9D1DC"
GRID = "#E6E9EE"
TEXT = "#1B2A41"
TEXT_MUTED = "#5B6675"

SERIES_ORDER = [PRIMARY, HIGHLIGHT, GREY_DARK, GREY_LIGHT]

RC = {
    "figure.dpi": 100,
    "savefig.dpi": 200,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 9,
    "axes.edgecolor": GRID,
    "axes.linewidth": 0.8,
    "axes.labelcolor": TEXT_MUTED,
    "axes.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": TEXT_MUTED,
    "ytick.color": TEXT_MUTED,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "lines.linewidth": 2.0,
    "svg.fonttype": "none",
    "svg.hashsalt": "weg",  # deterministic ids in SVG output
    "path.simplify": False,
}


def apply_style() -> None:
    plt.rcParams.update(RC)


def new_figure(width: float = 6.5, height: float = 3.6):
    apply_style()
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    return fig, ax


def save(fig, outdir: Path, name: str) -> tuple[Path, Path]:
    """Write <name>.svg and <name>.png with metadata stripped for byte-stable output."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    svg = outdir / f"{name}.svg"
    png = outdir / f"{name}.png"
    fig.savefig(svg, format="svg", bbox_inches="tight", metadata={"Date": None, "Creator": None})
    fig.savefig(png, format="png", bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    return svg, png
