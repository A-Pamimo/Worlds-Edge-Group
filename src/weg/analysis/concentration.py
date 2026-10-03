"""Destination concentration: Herfindahl-Hirschman index (0..1) and top-N shares."""
from __future__ import annotations

import pandas as pd


def shares(values: pd.Series) -> pd.Series:
    total = float(values.clip(lower=0).sum())
    return values.clip(lower=0) / total if total > 0 else values * float("nan")


def hhi(values: pd.Series) -> float:
    s = shares(values)
    return float((s**2).sum())


def top_n_share(values: pd.Series, n: int = 3) -> float:
    s = shares(values).sort_values(ascending=False)
    return float(s.head(n).sum())


def concentration(panel: pd.DataFrame, window: list[str], exclude: list[str] | None = None, n: int = 3) -> dict:
    """Concentration of a period x destination panel summed over a window."""
    idx = [p for p in panel.index if window[0] <= p <= window[1]]
    cols = [c for c in panel.columns if c not in (exclude or [])]
    totals = panel.reindex(idx)[cols].fillna(0.0).sum(axis=0)
    return {
        "hhi": hhi(totals),
        f"top{n}_share": top_n_share(totals, n),
        "n_destinations": int((totals > 0).sum()),
        "total": float(totals.sum()),
    }
