"""Diversion accounting: volume lost to one market and where it reappeared.

All inputs are period x destination panels (actual and counterfactual) of the same
quantity unit. Nothing here knows about products or config.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DiversionResult:
    loss: pd.Series  # by period, >= 0
    gains: pd.DataFrame  # period x destination (excluding the lost market), signed
    positive_gain: pd.Series  # by period, sum of positive gains
    matched: pd.Series  # by period, min(loss, positive_gain)
    never_resold: pd.Series  # by period, loss - matched
    ranking: pd.DataFrame  # destination, gain, share_of_positive_gain
    loss_total: float
    positive_gain_total: float
    net_gain_total: float
    reappeared_share_monthly: float  # sum(matched) / sum(loss)
    reappeared_share_period: float  # min(1, sum(positive gain) / sum(loss))
    world_actual_total: float
    world_cf_total: float


def diversion(actual: pd.DataFrame, cf: pd.DataFrame, lost_market: str, window: list[str]) -> DiversionResult:
    idx = [p for p in actual.index if window[0] <= p <= window[1]]
    a = actual.reindex(idx).fillna(0.0)
    c = cf.reindex(idx).reindex(columns=a.columns).fillna(0.0)
    if lost_market not in a.columns:
        raise KeyError(f"{lost_market!r} not in panel columns")
    loss = (c[lost_market] - a[lost_market]).clip(lower=0.0)
    others = [d for d in a.columns if d != lost_market]
    gains = a[others] - c[others]
    positive = gains.clip(lower=0.0).sum(axis=1)
    matched = pd.concat([loss, positive], axis=1).min(axis=1)
    never = loss - matched
    loss_total = float(loss.sum())
    pos_total = float(positive.sum())
    dest_gain = gains.sum(axis=0).sort_values(ascending=False)
    pos_dest = dest_gain.clip(lower=0.0)
    ranking = pd.DataFrame(
        {
            "destination": dest_gain.index,
            "gain": dest_gain.values,
            "share_of_positive_gain": (pos_dest / pos_dest.sum()).values if pos_dest.sum() > 0 else 0.0,
        }
    ).reset_index(drop=True)
    return DiversionResult(
        loss=loss,
        gains=gains,
        positive_gain=positive,
        matched=matched,
        never_resold=never,
        ranking=ranking,
        loss_total=loss_total,
        positive_gain_total=pos_total,
        net_gain_total=float(gains.sum().sum()),
        reappeared_share_monthly=(float(matched.sum()) / loss_total) if loss_total > 0 else float("nan"),
        reappeared_share_period=(min(1.0, pos_total / loss_total)) if loss_total > 0 else float("nan"),
        world_actual_total=float(a.sum().sum()),
        world_cf_total=float(c.sum().sum()),
    )
