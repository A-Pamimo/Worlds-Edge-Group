"""Q3 Replacement: which suppliers gained share in China's own import data."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from weg.numbers import NumbersWriter

from . import common as C

TOP_N = 5


def run(cfg: dict, T: C.Tables, numbers: NumbersWriter, tables_dir: Path) -> dict:
    periods = C.all_periods(cfg)
    china = cfg["markets"]["china"]
    out: dict = {}
    for product, spec_p in cfg["products"].items():
        panel = C.comtrade_panel(T.ct, china, "M", spec_p["hs6"], "qty", periods)
        if panel.empty:
            numbers.add(f"q3.{product}.coverage_last_period", None, "YYYY-MM", "comtrade", note="No China import data in the clean table")
            continue
        wins = C.window_periods(cfg, product)
        avail = set(panel.index)
        rows = []
        for wname in ("pre", "shock", "relief"):
            wper = [p for p in (wins.get(wname) or []) if p in avail]
            if not wper:
                continue
            tot = panel.loc[wper].sum(axis=0)
            share = tot / tot.sum() if tot.sum() > 0 else tot * float("nan")
            rows.append(pd.DataFrame({"product": product, "window": wname, "partner": tot.index, "tonnes": tot.values,
                                      "share": share.values, "months": len(wper), "monthly_mean_t": tot.values / len(wper)}))
        df = pd.concat(rows, ignore_index=True)
        df.to_csv(tables_dir / f"q3_{product}_china_import_shares.csv", index=False)
        pre = df[df.window == "pre"].set_index("partner")
        shock = df[df.window == "shock"].set_index("partner")
        last = max(p for p in avail if p <= cfg["data"]["latest_period"])
        m = "q3_replacement.run"
        numbers.add(f"q3.{product}.coverage_last_period", last, "YYYY-MM", m, note="Last month of China import data available")
        if len(pre) and len(shock):
            numbers.add(f"q3.{product}.shock.months_covered", int(shock["months"].iloc[0]), "months", m, window="shock")
            numbers.add(f"q3.{product}.shock.china_total_monthly_change_pct",
                        float(shock["monthly_mean_t"].sum() / pre["monthly_mean_t"].sum() - 1.0) if pre["monthly_mean_t"].sum() else float("nan"),
                        "share", m, window="shock", note="China's monthly mean imports from all partners, shock vs pre")
            numbers.add(f"q3.{product}.pre.canada_share", float(pre["share"].get("CAN", 0.0)), "share", m, window="pre")
            numbers.add(f"q3.{product}.shock.canada_share", float(shock["share"].get("CAN", 0.0)), "share", m, window="shock")
            delta = (shock["share"].reindex(shock.index.union(pre.index)).fillna(0.0) - pre["share"].reindex(shock.index.union(pre.index)).fillna(0.0)).sort_values(ascending=False)
            gainers = delta[(delta > 0) & (delta.index != "CAN")].head(TOP_N)
            numbers.add(f"q3.{product}.shock.top_gainers", gainers.index.tolist(), "iso3", m, window="shock")
            numbers.add(f"q3.{product}.shock.top_gainer_share_change", [float(x) for x in gainers.values], "share", m, window="shock")
            numbers.add(f"q3.{product}.shock.top_gainer_monthly_t", [float(shock["monthly_mean_t"].get(g, 0.0)) for g in gainers.index], "tonnes", m, window="shock")
        out[product] = {"panel": panel, "shares": df}
    return out
