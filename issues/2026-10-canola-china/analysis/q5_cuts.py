"""Q5 Strategic cuts: province, new-buyer price gap, concentration, relief window."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from weg.analysis.concentration import concentration
from weg.analysis.diversion import diversion
from weg.analysis.seasonality import seasonally_adjust
from weg.analysis.unitvalue import gap_trend, unit_value
from weg.numbers import NumbersWriter

from . import common as C


def run(cfg: dict, T: C.Tables, numbers: NumbersWriter, tables_dir: Path, q1: dict, q2: dict) -> dict:
    out = {"province": _province(cfg, T, numbers, tables_dir, q1, q2), "gap": _gap(cfg, numbers, tables_dir, q1, q2),
           "concentration": _concentration(cfg, numbers, tables_dir, q1), "relief": _relief(cfg, numbers, tables_dir, q1, q2)}
    return out


def _province(cfg, T, numbers, tables_dir, q1, q2) -> pd.DataFrame | None:
    if T.prov is None:
        numbers.add("q5.province.available", False, "bool", "q5_cuts._province", note="No province table in data/clean")
        return None
    numbers.add("q5.province.available", True, "bool", "q5_cuts._province")
    periods = C.all_periods(cfg)
    specs = C.cf_specs(cfg)
    min_obs = int(cfg["seasonality"]["min_nonzero_months"])
    china = cfg["markets"]["china"]
    rows = []
    for product, spec_p in cfg["products"].items():
        if product not in q1:
            continue
        wins = C.window_periods(cfg, product)
        uv_nat = q2[product]["uv"]
        sub = T.prov[T.prov["hs6"].isin(spec_p["hs6"])]
        for prov in sorted(sub["province"].unique()):
            panel = sub[sub["province"] == prov].pivot_table(index="period", columns="partner_iso3", values="value_cad", aggfunc="sum", fill_value=0.0)
            panel = panel.reindex(periods).fillna(0.0)
            panel = panel.loc[:, panel.sum(axis=0) > 0]
            panel.columns.name = None
            if china not in panel.columns:
                continue
            for cf_name, spec in specs.items():
                cf = C.cf_panel(panel, periods, spec, min_obs)
                r = diversion(panel, cf, china, [wins["shock"][0], wins["shock"][-1]])
                # estimated tonnes: provincial value / national unit value (same HS6 group, destination, month)
                uv_china = uv_nat[china].reindex(wins["shock"]) if china in uv_nat.columns else pd.Series(dtype=float)
                lost_t_est = float((r.loss / uv_china).replace([float("inf")], float("nan")).dropna().sum()) if len(uv_china) else float("nan")
                rows.append({"product": product, "province": prov, "counterfactual": cf_name, "lost_revenue_cad": r.loss_total,
                             "reappeared_value_cad": float(r.matched.sum()), "net_cost_cad": float(r.never_resold.sum()),
                             "lost_tonnes_estimated": lost_t_est, "reappeared_share": r.reappeared_share_monthly})
                k = f"q5.province.{product}.{prov}.{cf_name}.shock"
                m = "q5_cuts._province"
                numbers.add(f"{k}.lost_revenue_cad", r.loss_total, "CAD", m, window="shock", counterfactual=cf_name,
                            note="Value basis: sum max(counterfactual value to China - actual, 0) on the province x destination series")
                numbers.add(f"{k}.reappeared_value_cad", float(r.matched.sum()), "CAD", m, window="shock", counterfactual=cf_name)
                numbers.add(f"{k}.net_cost_cad", float(r.never_resold.sum()), "CAD", m, window="shock", counterfactual=cf_name,
                            note="Lost revenue not matched by value gains elsewhere from the same province; discount on resold volume not separable at province level")
                numbers.add(f"{k}.lost_tonnes_estimated", lost_t_est, "tonnes", m, window="shock", counterfactual=cf_name, estimated=True,
                            note="Provincial lost value divided by the national unit value for the same product, destination and month")
    df = pd.DataFrame(rows)
    df.to_csv(tables_dir / "q5_province_cost.csv", index=False)
    if len(df):
        for cf_name in specs:
            tot = df[df.counterfactual == cf_name].groupby("province")["net_cost_cad"].sum().sort_values(ascending=False)
            numbers.add(f"q5.province.total.{cf_name}.shock.net_cost_by_province_cad", {k: float(v) for k, v in tot.items()}, "CAD",
                        "q5_cuts._province", window="shock", counterfactual=cf_name)
    return df


def _gap(cfg, numbers, tables_dir, q1, q2) -> pd.DataFrame:
    china = cfg["markets"]["china"]
    thr = cfg["price"]["gap_trend"]
    rows = []
    for product in q1:
        gainers = q2[product]["gainers"]
        if not gainers:
            continue
        uv, factors, value = q2[product]["uv"], q2[product]["factors"], q2[product]["value"]
        qty = q1[product]["actual"]
        wins = C.window_periods(cfg, product)
        nb_uv = unit_value(value[gainers].sum(axis=1), qty[gainers].sum(axis=1) * C.TONNE_KG)
        nb_sa = seasonally_adjust(nb_uv.fillna(0.0), factors["__fallback__"]).where(nb_uv > 0)
        china_sa = seasonally_adjust(uv[china].fillna(0.0), factors[china]).where(uv[china] > 0)
        china_pre = float(china_sa.reindex(wins["pre"]).dropna().mean())
        gap = (nb_sa.reindex(wins["shock"]) - china_pre)
        trend = gap_trend(gap, thr["narrowing_if_t_below"], thr["widening_if_t_above"])
        k = f"q5.{product}.gap"
        m = "weg.analysis.unitvalue.gap_trend"
        numbers.add(f"{k}.china_pre_sa_cad_t", china_pre, "CAD/tonne", m, window="pre")
        numbers.add(f"{k}.new_buyers_shock_sa_cad_t", float(nb_sa.reindex(wins["shock"]).dropna().mean()), "CAD/tonne", m, window="shock")
        numbers.add(f"{k}.mean_gap_cad_t", float(gap.dropna().mean()), "CAD/tonne", m, window="shock",
                    note="New-buyer SA unit value minus China's pre-event SA unit value; negative = new buyers pay less")
        numbers.add(f"{k}.mean_gap_pct", float(gap.dropna().mean() / china_pre) if china_pre else float("nan"), "share", m, window="shock")
        numbers.add(f"{k}.slope_cad_t_per_month", trend["slope"], "CAD/tonne/month", m, window="shock", note="OLS slope of |gap| on time")
        numbers.add(f"{k}.t_stat", trend["t_stat"], "t", m, window="shock")
        numbers.add(f"{k}.classification", trend["classification"], "label", m, window="shock",
                    note=f"narrowing if t < {thr['narrowing_if_t_below']}, widening if t > {thr['widening_if_t_above']}, else stable")
        rows.append(pd.DataFrame({"product": product, "period": gap.index, "gap_cad_t": gap.values,
                                  "new_buyers_sa_cad_t": nb_sa.reindex(wins["shock"]).values, "china_pre_sa_cad_t": china_pre}))
    df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    df.to_csv(tables_dir / "q5_gap.csv", index=False)
    return df


def _concentration(cfg, numbers, tables_dir, q1) -> pd.DataFrame:
    china = cfg["markets"]["china"]
    rows = []
    for product in q1:
        wins = C.window_periods(cfg, product)
        actual = q1[product]["actual"]
        for wname in ("pre", "shock", "relief"):
            wper = wins.get(wname)
            if not wper:
                continue
            c = concentration(actual, [wper[0], wper[-1]], exclude=[china], n=3)
            rows.append({"product": product, "window": wname, **c})
            k = f"q5.{product}.concentration.{wname}"
            numbers.add(f"{k}.hhi_ex_china", c["hhi"], "index", "weg.analysis.concentration", window=wname, note="HHI (0-1) of non-China destinations by tonnes")
            numbers.add(f"{k}.top3_share_ex_china", c["top3_share"], "share", "weg.analysis.concentration", window=wname)
            numbers.add(f"{k}.n_destinations_ex_china", c["n_destinations"], "count", "weg.analysis.concentration", window=wname)
    df = pd.DataFrame(rows)
    df.to_csv(tables_dir / "q5_concentration.csv", index=False)
    return df


def _relief(cfg, numbers, tables_dir, q1, q2) -> pd.DataFrame:
    china = cfg["markets"]["china"]
    rows = []
    for product in q1:
        wins = C.window_periods(cfg, product)
        if not wins.get("relief"):
            continue
        actual, cf = q1[product]["actual"], q1[product]["cf"][C.HEADLINE_CF]
        a = actual[china].reindex(wins["relief"]).sum()
        c = cf[china].reindex(wins["relief"]).sum()
        a_shock = actual[china].reindex(wins["shock"]).mean()
        k = f"q5.relief.{product}"
        m = "q5_cuts._relief"
        numbers.add(f"{k}.china_volume_ratio_to_cf", float(a / c) if c else float("nan"), "ratio", m, window="relief", counterfactual=C.HEADLINE_CF,
                    note="Actual China volume in the relief window over counterfactual B; 1 = fully returned")
        numbers.add(f"{k}.china_monthly_t_relief_vs_shock", float(actual[china].reindex(wins["relief"]).mean() / a_shock) if a_shock else float("nan"),
                    "ratio", m, window="relief")
        rows.append({"product": product, "china_actual_relief_t": float(a), "china_cf_relief_t": float(c), "china_monthly_mean_shock_t": float(a_shock)})
    df = pd.DataFrame(rows)
    df.to_csv(tables_dir / "q5_relief.csv", index=False)
    return df
