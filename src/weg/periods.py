"""Period helpers. Periods are 'YYYY-MM' strings everywhere in the clean tables."""
from __future__ import annotations

import pandas as pd


def shift(period: str, months: int) -> str:
    return (pd.Period(period, freq="M") + months).strftime("%Y-%m")


def month_range(start: str, end: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]


def months_between(start: str, end: str) -> int:
    """Number of months from start to end (end - start)."""
    return (pd.Period(end, freq="M") - pd.Period(start, freq="M")).n


def month_of(period: str) -> int:
    return int(period[5:7])


def in_window(period: str, window: list[str] | tuple[str, str]) -> bool:
    return window[0] <= period <= window[1]


def crop_year(period: str, start_month: int = 8) -> str:
    """Crop year label, e.g. 2024-08 -> '2024/25' when start_month=8."""
    y, m = int(period[:4]), int(period[5:7])
    start = y if m >= start_month else y - 1
    return f"{start}/{(start + 1) % 100:02d}"
