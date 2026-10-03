"""Q4 Cost: revenue lost on volume never resold plus the discount on volume that was."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from weg.analysis.counterfactual import counterfactual, same_months_prior_year
from weg.numbers import NumbersWriter

from . import common as C


def _cf_series(series: pd.Series, periods: list[str], spec: dict, min_obs: int, fallback: pd.Series | None = None) -> pd.Series:
    s = series.fillna(0.0)
    cf = counterfactual(s, periods, spec, min_obs)
    if cf is None:
        cf = same_months_prior_year(s, periods)
    if fallback is not None:
        cf = cf.where(cf > 0, fallback.reindex(periods))
    return cf


def run(cfg: dict, T: C.Tables, numbers: NumbersWriter, tables_dir: Path, q1: dict, q2: dict) -> dict:
    periods = C.all_periods(cfg)
    specs = C.cf_specs(cfg)
    min_obs = int(cfg["seasonality"]["min_nonzero_months"])
    china = cfg["markets"]["china"]
    totals: dict[tuple[str, str], dict[str, float]] = {}
    rows = []
    for product in q1:
        uv = q2[product]["uv"]
        bench = q2[product]["bench"]
        wins = C.window_periods(cfg, product)
        for cf_name, spec in specs.items():
            for wname in ("shock", "relief"):
                r = q1[product]["div"].get((cf_name, wname))
                if r is None:
                    continue
                wper = wins[wname]
                cf_uv_china = _cf_series(uv[china], wper, spec, min_obs, fallback=bench)
                never_rev = float((r.never_resold * cf_uv_china.reindex(wper)).sum())
                pos = r.gains.clip(lower=0.0)
                share = pos.div(pos.sum(axis=1).replace(0, float("nan")), axis=0).fillna(0.0)
                alloc = share.mul(r.matched, axis=0)  # tonnes of matched volume per destination-month
                discount = 0.0
                disc_rows = {}
                for dest in alloc.columns:
                    if alloc[dest].sum() <= 0:
                        continue
                    cf_uv_d = _cf_series(uv[dest], wper, spec, min_obs, fallback=bench)
                    actual_uv_d = uv[dest].reindex(wper)
                    gap = (cf_uv_d.reindex(wper) - actual_uv_d).fillna(0.0)
                    d = float((alloc[dest] * gap).sum())
                    disc_rows[dest] = d
                    discount += d
                cost = never_rev + discount
                # period-matching sensitivity: match totals over the window rather than month by month
                never_period = max(r.loss_total - r.positive_gain_total, 0.0)
                mean_cf_uv = float(cf_uv_china.reindex(wper).mean())
                cost_period = never_period * mean_cf_uv + discount
                k = f"q4.{product}.{cf_name}.{wname}"
                m = "q4_cost.run"
                numbers.add(f"{k}.never_resold_revenue_cad", never_rev, "CAD", m, window=wname, counterfactual=cf_name,
                            note="Never-resold tonnes x counterfactual China unit value (CAD/t), month by month")
                numbers.add(f"{k}.discount_cad", discount, "CAD", m, window=wname, counterfactual=cf_name,
                            note="Matched tonnes x (counterfactual destination unit value - actual), signed; negative = premium")
                numbers.add(f"{k}.cost_cad", cost, "CAD", m, window=wname, counterfactual=cf_name)
                numbers.add(f"{k}.cost_cad_period_matching", cost_period, "CAD", m, window=wname, counterfactual=cf_name,
                            note="Sensitivity: never-resold volume from window totals instead of monthly matching")
                numbers.add(f"{k}.cf_china_unit_value_mean_cad_t", mean_cf_uv, "CAD/tonne", m, window=wname, counterfactual=cf_name)
                totals.setdefault((cf_name, wname), {"never": 0.0, "discount": 0.0, "cost": 0.0, "cost_period": 0.0})
                for key, val in (("never", never_rev), ("discount", discount), ("cost", cost), ("cost_period", cost_period)):
                    totals[(cf_name, wname)][key] += val
                rows.append({"product": product, "counterfactual": cf_name, "window": wname, "never_resold_revenue_cad": never_rev,
                             "discount_cad": discount, "cost_cad": cost, "cost_cad_period_matching": cost_period,
                             **{f"discount_{d}_cad": v for d, v in disc_rows.items()}})
    for (cf_name, wname), t in totals.items():
        k = f"q4.total.{cf_name}.{wname}"
        numbers.add(f"{k}.never_resold_revenue_cad", t["never"], "CAD", "q4_cost.run", window=wname, counterfactual=cf_name)
        numbers.add(f"{k}.discount_cad", t["discount"], "CAD", "q4_cost.run", window=wname, counterfactual=cf_name)
        numbers.add(f"{k}.cost_cad", t["cost"], "CAD", "q4_cost.run", window=wname, counterfactual=cf_name, note="Sum over products")
        numbers.add(f"{k}.cost_cad_period_matching", t["cost_period"], "CAD", "q4_cost.run", window=wname, counterfactual=cf_name)
    pd.DataFrame(rows).to_csv(tables_dir / "q4_cost.csv", index=False)
    return {"rows": rows, "totals": totals}
