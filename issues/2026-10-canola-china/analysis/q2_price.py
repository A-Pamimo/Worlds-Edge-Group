"""Q2 Price: did new destinations pay less than pre-event prices in those same markets, net of seasonality."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from weg.analysis.seasonality import seasonally_adjust
from weg.analysis.unitvalue import price_change, unit_value
from weg.numbers import NumbersWriter

from . import common as C

TOP_N = 5


def run(cfg: dict, T: C.Tables, numbers: NumbersWriter, tables_dir: Path, q1: dict) -> dict:
    periods = C.all_periods(cfg)
    china = cfg["markets"]["china"]
    min_pre = int(cfg["price"]["min_pre_months"])
    out: dict = {}
    for product, spec_p in cfg["products"].items():
        if product not in q1:
            continue
        qty = q1[product]["actual"]
        value = C.product_panel(T.ca, spec_p["hs6"], "value_cad", periods).reindex(columns=qty.columns).fillna(0.0)
        uv = C.unit_value_panel(value, qty)
        factors = C.factor_lookup(uv.fillna(0.0), cfg)
        wins = C.window_periods(cfg, product)
        # benchmark: all destinations except China, volume weighted
        others = [c for c in qty.columns if c != china]
        bench = unit_value(value[others].sum(axis=1), qty[others].sum(axis=1) * C.TONNE_KG)
        bench_f = factors["__fallback__"]
        div = q1[product]["div"].get((C.HEADLINE_CF, "shock"))
        gainers = [d for d in div.ranking["destination"] if d != china and div.ranking.set_index("destination").loc[d, "gain"] > 0] if div else []
        focus = [china] + [d for d in qty.loc[wins["shock"]].sum().sort_values(ascending=False).index if d != china][:TOP_N]
        rows = []
        for dest in focus:
            for wname in ("shock", "relief"):
                wper = wins.get(wname)
                if not wper:
                    continue
                pre_w, post_w = [wins["pre"][0], wins["pre"][-1]], [wper[0], wper[-1]]
                nominal = price_change(uv[dest], pre_w, post_w, factors[dest], min_pre)
                rel = price_change((uv[dest] / bench).replace([float("inf")], float("nan")), pre_w, post_w, None, min_pre)
                rows.append({"product": product, "destination": dest, "window": wname, **{f"sa_{k}": v for k, v in nominal.items()},
                             **{f"rel_{k}": v for k, v in rel.items()}})
                k = f"q2.{product}.{dest}.{wname}"
                m = "weg.analysis.unitvalue.price_change"
                numbers.add(f"{k}.pre_mean_cad_t", nominal["pre_mean"], "CAD/tonne", m, window=wname,
                            note="Seasonally adjusted mean unit value over the pre window in this destination")
                numbers.add(f"{k}.post_mean_cad_t", nominal["post_mean"], "CAD/tonne", m, window=wname)
                numbers.add(f"{k}.pct_change_sa", nominal["pct_change"], "share", m, window=wname,
                            note="Seasonally adjusted unit value, post mean vs pre mean, same destination")
                numbers.add(f"{k}.pct_change_relative", rel["pct_change"], "share", m, window=wname,
                            note="Change in the ratio of this destination's unit value to the all-destinations-ex-China unit value (nets out world price moves)")
                numbers.add(f"{k}.n_pre_months", nominal["n_pre"], "months", m, window=wname)
        # new buyers aggregate: destinations with positive gains, volume-weighted
        if gainers:
            nb_uv = unit_value(value[gainers].sum(axis=1), qty[gainers].sum(axis=1) * C.TONNE_KG)
            nb = price_change(nb_uv, [wins["pre"][0], wins["pre"][-1]], [wins["shock"][0], wins["shock"][-1]], bench_f, min_pre)
            nb_rel = price_change((nb_uv / bench), [wins["pre"][0], wins["pre"][-1]], [wins["shock"][0], wins["shock"][-1]], None, min_pre)
            numbers.add(f"q2.{product}.new_buyers.shock.pct_change_sa", nb["pct_change"], "share", "weg.analysis.unitvalue.price_change",
                        window="shock", note=f"Volume-weighted unit value across destinations with positive gains under CF {C.HEADLINE_CF}")
            numbers.add(f"q2.{product}.new_buyers.shock.pct_change_relative", nb_rel["pct_change"], "share", "weg.analysis.unitvalue.price_change", window="shock")
            numbers.add(f"q2.{product}.new_buyers.members", gainers, "iso3", "q1 ranking", window="shock", counterfactual=C.HEADLINE_CF)
        pd.DataFrame(rows).to_csv(tables_dir / f"q2_{product}_price_changes.csv", index=False)
        sa = pd.DataFrame({d: seasonally_adjust(uv[d].fillna(0.0), factors[d]).where(uv[d] > 0) for d in focus})
        sa["benchmark_ex_china"] = seasonally_adjust(bench.fillna(0.0), bench_f).where(bench > 0)
        sa.rename_axis("period").to_csv(tables_dir / f"q2_{product}_unit_values_sa.csv")
        out[product] = {"uv": uv, "factors": factors, "bench": bench, "gainers": gainers, "value": value}
    return out
