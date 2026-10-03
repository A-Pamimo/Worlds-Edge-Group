"""Counterfactual volume and price paths.

A  same months of the prior year (no model; confounded by crop size, stated in METHODS)
B  trend + seasonal fit on 2019-01..2024-12 projected forward
B' same as B with 2020-01..2021-12 excluded from the fit (sensitivity)
Specs come from config.yaml `counterfactuals`; this module never hard-codes a window.
"""
from __future__ import annotations

import pandas as pd

from weg import periods as P
from weg.analysis.seasonality import fit_trend_seasonal


def same_months_prior_year(series: pd.Series, periods: list[str]) -> pd.Series:
    s = series.copy()
    vals = [float(s.get(P.shift(p, -12), 0.0)) for p in periods]
    return pd.Series(vals, index=list(periods), name="cf")


def trend_seasonal(
    series: pd.Series,
    periods: list[str],
    fit_start: str,
    fit_end: str,
    exclude: list[list[str]] | None = None,
    min_obs: int = 24,
) -> pd.Series | None:
    fit = fit_trend_seasonal(series, fit_start, fit_end, exclude, min_obs)
    return None if fit is None else fit.predict(periods)


def counterfactual(series: pd.Series, periods: list[str], spec: dict, min_obs: int = 24) -> pd.Series | None:
    name = spec["name"]
    if name == "same_months_prior_year":
        return same_months_prior_year(series, periods)
    if name.startswith("trend_seasonal"):
        return trend_seasonal(series, periods, spec["fit_start"], spec["fit_end"], spec.get("exclude"), min_obs)
    raise ValueError(f"unknown counterfactual {name!r}")


def counterfactual_panel(
    panel: pd.DataFrame, periods: list[str], spec: dict, min_obs: int = 24, fallback: pd.Series | None = None
) -> pd.DataFrame:
    """Apply a counterfactual to every column of a period x destination panel.

    Columns whose model cannot be fit (too few observations) fall back to
    `fallback` scaled by the column's share of the fallback series in the fit
    window; if no fallback is given they get counterfactual A.
    """
    out = {}
    for col in panel.columns:
        cf = counterfactual(panel[col], periods, spec, min_obs)
        if cf is None:
            cf = same_months_prior_year(panel[col], periods)
        out[col] = cf
    return pd.DataFrame(out, index=list(periods))
