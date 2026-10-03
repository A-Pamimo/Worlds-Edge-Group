"""Reconcile Canada-reported exports with partner-reported imports.

Partner imports are CIF and lag exports by the shipping time, so single months do not
match. We compare annual sums and 3-month rolling sums at lags 0..2 and report the
ratio partner/Canada; the best lag minimises the mean absolute log ratio of rolling sums.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from weg import periods as P


def _aligned(exports: pd.Series, imports: pd.Series, lag: int) -> pd.DataFrame:
    """Align partner imports in month t+lag with Canadian exports in month t."""
    idx = sorted(set(exports.index) | {P.shift(p, -lag) for p in imports.index})
    e = exports.reindex(idx).fillna(0.0)
    i = pd.Series({P.shift(p, -lag): v for p, v in imports.items()}).reindex(idx).fillna(0.0)
    return pd.DataFrame({"exports": e, "imports_lagged": i}, index=idx)


def reconcile(exports: pd.Series, imports: pd.Series, lags: list[int] = (0, 1, 2), roll: int = 3) -> dict:
    """Return per-lag annual ratios, rolling ratios, and the best lag."""
    per_lag = {}
    for lag in lags:
        df = _aligned(exports, imports, lag)
        df["year"] = [p[:4] for p in df.index]
        annual = df.groupby("year")[["exports", "imports_lagged"]].sum()
        annual["ratio"] = annual["imports_lagged"] / annual["exports"].replace(0, np.nan)
        r = df[["exports", "imports_lagged"]].rolling(roll).sum()
        rolling = (r["imports_lagged"] / r["exports"].replace(0, np.nan)).dropna()
        score = float(np.abs(np.log(rolling[rolling > 0])).mean()) if (rolling > 0).any() else np.inf
        per_lag[lag] = {"annual": annual, "rolling": rolling, "score": score}
    best = min(per_lag, key=lambda k: per_lag[k]["score"])
    return {"per_lag": per_lag, "best_lag": best}


def within_tolerance(annual: pd.DataFrame, band: list[float], min_exports: float = 0.0) -> pd.DataFrame:
    out = annual.copy()
    out["within"] = out["ratio"].between(band[0], band[1]) | (out["exports"] <= min_exports)
    return out
