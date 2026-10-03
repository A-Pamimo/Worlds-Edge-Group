"""Seasonal factors and trend+seasonal fits.

Model (used both for seasonal adjustment and counterfactual B):
    log(y_t) = a + b * t + sum_{k=2..12} m_k * 1[month_t = k] + e_t
fit by ordinary least squares on the fit window, with optional excluded sub-windows
(e.g. 2020-01..2021-12 for the B' sensitivity). Zero observations cannot enter a log
fit and are dropped; a series with fewer than `min_obs` positive observations in the
fit window returns None so callers can fall back to product-level factors.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from weg import periods as P


@dataclass(frozen=True)
class TrendSeasonalFit:
    origin: str  # period where t = 0
    intercept: float
    trend: float  # per month, in log units
    month_effects: tuple[float, ...]  # 12 values, January = 0 by construction
    n_obs: int
    resid_sd: float

    def predict(self, periods: list[str]) -> pd.Series:
        t = np.array([P.months_between(self.origin, p) for p in periods], dtype=float)
        m = np.array([self.month_effects[P.month_of(p) - 1] for p in periods])
        return pd.Series(np.exp(self.intercept + self.trend * t + m), index=list(periods), name="cf")

    def factors(self) -> pd.Series:
        """Multiplicative month-of-year factors normalised to geometric mean 1."""
        eff = np.array(self.month_effects)
        eff = eff - eff.mean()
        return pd.Series(np.exp(eff), index=range(1, 13), name="factor")


def _design(periods: list[str], origin: str) -> np.ndarray:
    t = np.array([P.months_between(origin, p) for p in periods], dtype=float)
    X = np.zeros((len(periods), 13))
    X[:, 0] = 1.0
    X[:, 1] = t
    for i, p in enumerate(periods):
        k = P.month_of(p)
        if k > 1:
            X[:, 1 + k - 1][i] = 1.0  # columns 2..12 are months 2..12
    return X


def fit_trend_seasonal(
    series: pd.Series,
    fit_start: str,
    fit_end: str,
    exclude: list[list[str]] | None = None,
    min_obs: int = 24,
) -> TrendSeasonalFit | None:
    """`series` is indexed by 'YYYY-MM'. Missing periods count as zero (no trade)."""
    exclude = exclude or []
    window = P.month_range(fit_start, fit_end)
    s = series.reindex(window).fillna(0.0)
    keep = [
        p for p in window
        if s[p] > 0 and not any(P.in_window(p, ex) for ex in exclude)
    ]
    if len(keep) < min_obs or len({P.month_of(p) for p in keep}) < 12:
        return None
    y = np.log(s[keep].to_numpy(dtype=float))
    X = _design(keep, fit_start)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(keep) - X.shape[1], 1)
    effects = (0.0,) + tuple(float(b) for b in beta[2:])
    return TrendSeasonalFit(
        origin=fit_start,
        intercept=float(beta[0]),
        trend=float(beta[1]),
        month_effects=effects,
        n_obs=len(keep),
        resid_sd=float(np.sqrt((resid**2).sum() / dof)),
    )


def seasonal_factors(
    series: pd.Series, fit_start: str, fit_end: str, exclude=None, min_obs: int = 24
) -> pd.Series | None:
    fit = fit_trend_seasonal(series, fit_start, fit_end, exclude, min_obs)
    return None if fit is None else fit.factors()


def seasonally_adjust(series: pd.Series, factors: pd.Series) -> pd.Series:
    """Divide each observation by its month-of-year factor."""
    f = np.array([factors[P.month_of(p)] for p in series.index])
    return series / f
