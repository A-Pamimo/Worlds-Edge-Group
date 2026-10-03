"""Unit values, currency conversion, price changes and the new-buyer price gap."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from weg import periods as P
from weg.analysis.seasonality import seasonally_adjust

KG_PER_TONNE = 1000.0


def unit_value(value: pd.Series, qty_kg: pd.Series) -> pd.Series:
    """Value per tonne; NaN where quantity is zero or missing."""
    tonnes = qty_kg / KG_PER_TONNE
    return value.where(tonnes > 0) / tonnes.where(tonnes > 0)


def usd_to_cad(df: pd.DataFrame, fx: pd.DataFrame, value_col: str = "value_usd", pair: str = "FXMUSDCAD") -> pd.DataFrame:
    rates = fx.loc[fx["pair"] == pair, ["period", "rate"]].rename(columns={"rate": "_rate"})
    out = df.merge(rates, on="period", how="left", validate="many_to_one")
    if out["_rate"].isna().any():
        missing = sorted(out.loc[out["_rate"].isna(), "period"].unique())[:5]
        raise ValueError(f"no {pair} rate for periods {missing}")
    out["value_cad"] = out[value_col] * out["_rate"]
    return out.drop(columns="_rate")


def price_change(uv: pd.Series, pre: list[str], post: list[str], factors: pd.Series | None = None, min_pre_months: int = 3) -> dict:
    """Seasonally adjusted mean unit value pre vs post for one series (index 'YYYY-MM')."""
    s = uv.dropna()
    s = s[s > 0]
    if factors is not None:
        s = seasonally_adjust(s, factors)
    pre_s = s[[p for p in s.index if P.in_window(p, pre)]]
    post_s = s[[p for p in s.index if P.in_window(p, post)]]
    if len(pre_s) < min_pre_months or len(post_s) == 0:
        return {"pre_mean": np.nan, "post_mean": np.nan, "pct_change": np.nan, "n_pre": len(pre_s), "n_post": len(post_s)}
    pre_mean, post_mean = float(pre_s.mean()), float(post_s.mean())
    return {
        "pre_mean": pre_mean,
        "post_mean": post_mean,
        "pct_change": post_mean / pre_mean - 1.0,
        "n_pre": int(len(pre_s)),
        "n_post": int(len(post_s)),
    }


def weighted_unit_value(value: pd.DataFrame, qty_kg: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Volume-weighted unit value across destinations, by period."""
    v = value[columns].sum(axis=1)
    q = qty_kg[columns].sum(axis=1)
    return unit_value(v, q)


def gap_trend(gap: pd.Series, narrowing_if_t_below: float = -2.0, widening_if_t_above: float = 2.0) -> dict:
    """OLS slope of a gap series on time; classification by t-statistic on the slope.

    A *negative* slope on |gap| means narrowing. Callers pass the signed gap
    (new-buyer price minus the reference price); we classify on the absolute gap so
    "narrowing" means the two prices are converging whichever side is higher.
    """
    g = gap.dropna()
    if len(g) < 4:
        return {"slope": np.nan, "t_stat": np.nan, "p_value": np.nan, "n": int(len(g)), "classification": "insufficient"}
    y = g.abs().to_numpy(dtype=float)
    t = np.arange(len(y), dtype=float)
    model = sm.OLS(y, sm.add_constant(t)).fit()
    slope, tstat, pval = float(model.params[1]), float(model.tvalues[1]), float(model.pvalues[1])
    if tstat < narrowing_if_t_below:
        cls = "narrowing"
    elif tstat > widening_if_t_above:
        cls = "widening"
    else:
        cls = "stable"
    return {"slope": slope, "t_stat": tstat, "p_value": pval, "n": int(len(g)), "classification": cls}
