"""Q1 Diversion: volume lost to China after each event, share reappearing elsewhere, and where."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from weg.analysis.diversion import DiversionResult, diversion
from weg.numbers import NumbersWriter

from . import common as C

TOP_N = 5


def run(cfg: dict, T: C.Tables, numbers: NumbersWriter, tables_dir: Path) -> dict:
    periods = C.all_periods(cfg)
    specs = C.cf_specs(cfg)
    min_obs = int(cfg["seasonality"]["min_nonzero_months"])
    china = cfg["markets"]["china"]
    results: dict = {}
    for product, spec_p in cfg["products"].items():
        actual = C.product_panel(T.ca, spec_p["hs6"], "qty", periods)
        if china not in actual.columns:
            continue
        wins = C.window_periods(cfg, product)
        results[product] = {"actual": actual, "cf": {}, "div": {}}
        for cf_name, spec in specs.items():
            cf = C.cf_panel(actual, periods, spec, min_obs)
            results[product]["cf"][cf_name] = cf
            for wname, wper in wins.items():
                if wname == "pre" or not wper:
                    continue
                r = diversion(actual, cf, china, [wper[0], wper[-1]])
                results[product]["div"][(cf_name, wname)] = r
                _write(numbers, product, cf_name, wname, r)
                numbers.add(f"q1.{product}.{cf_name}.{wname}.china_actual_t", float(actual[china].reindex(wper).sum()), "tonnes",
                            "q1_diversion.run", window=wname, counterfactual=cf_name)
                numbers.add(f"q1.{product}.{cf_name}.{wname}.china_cf_t", float(cf[china].reindex(wper).sum()), "tonnes",
                            "q1_diversion.run", window=wname, counterfactual=cf_name)
                r.ranking.to_csv(tables_dir / f"q1_{product}_{cf_name}_{wname}_ranking.csv", index=False)
                pd.DataFrame({"loss_t": r.loss, "positive_gain_t": r.positive_gain, "matched_t": r.matched,
                              "never_resold_t": r.never_resold}).rename_axis("period").to_csv(
                    tables_dir / f"q1_{product}_{cf_name}_{wname}_monthly.csv")
        actual.rename_axis("period").to_csv(tables_dir / f"q1_{product}_actual_tonnes.csv")
        results[product]["cf"][C.HEADLINE_CF].rename_axis("period").to_csv(tables_dir / f"q1_{product}_cf_{C.HEADLINE_CF}_tonnes.csv")
    _transshipment(cfg, T, numbers, tables_dir, results)
    return results


def _write(n: NumbersWriter, product: str, cf: str, window: str, r: DiversionResult) -> None:
    k = f"q1.{product}.{cf}.{window}"
    m = "weg.analysis.diversion.diversion"
    n.add(f"{k}.loss_t", r.loss_total, "tonnes", m, window=window, counterfactual=cf,
          note="Sum over window of max(counterfactual China volume - actual, 0)")
    n.add(f"{k}.reappeared_share", r.reappeared_share_monthly, "share", m, window=window, counterfactual=cf,
          note="Monthly matching: sum(min(loss_t, positive gains_t)) / sum(loss_t)")
    n.add(f"{k}.reappeared_share_period", r.reappeared_share_period, "share", m, window=window, counterfactual=cf,
          note="Period matching: min(1, sum positive gains / sum loss)")
    n.add(f"{k}.never_resold_t", float(r.never_resold.sum()), "tonnes", m, window=window, counterfactual=cf)
    n.add(f"{k}.positive_gain_t", r.positive_gain_total, "tonnes", m, window=window, counterfactual=cf)
    n.add(f"{k}.net_gain_t", r.net_gain_total, "tonnes", m, window=window, counterfactual=cf,
          note="Signed sum of gains over all non-China destinations")
    n.add(f"{k}.world_actual_t", r.world_actual_total, "tonnes", m, window=window, counterfactual=cf)
    n.add(f"{k}.world_cf_t", r.world_cf_total, "tonnes", m, window=window, counterfactual=cf)
    n.add(f"{k}.world_change_pct", (r.world_actual_total / r.world_cf_total - 1.0) if r.world_cf_total else float("nan"),
          "share", m, window=window, counterfactual=cf)
    top = r.ranking.head(TOP_N)
    n.add(f"{k}.top_destinations", top["destination"].tolist(), "iso3", m, window=window, counterfactual=cf)
    n.add(f"{k}.top_destination_gain_t", [float(x) for x in top["gain"]], "tonnes", m, window=window, counterfactual=cf)
    n.add(f"{k}.top_destination_share_of_gain", [float(x) for x in top["share_of_positive_gain"]], "share", m,
          window=window, counterfactual=cf)


def _transshipment(cfg: dict, T: C.Tables, numbers: NumbersWriter, tables_dir: Path, results: dict) -> None:
    """Screen top gainers: did their own imports from Canada rise, and did their exports to China rise?"""
    periods = C.all_periods(cfg)
    china = cfg["markets"]["china"]
    rows = []
    for product, res in results.items():
        r = res["div"].get((C.HEADLINE_CF, "shock"))
        if r is None:
            continue
        wins = C.window_periods(cfg, product)
        hs6 = cfg["products"][product]["hs6"]
        for dest in r.ranking.head(TOP_N)["destination"]:
            if not str(dest).isalpha():
                continue
            gain = float(r.ranking.set_index("destination").loc[dest, "gain"])
            imp = C.comtrade_panel(T.ct, dest, "M", hs6, "qty", periods)
            exp = C.comtrade_panel(T.ct, dest, "X", hs6, "qty", periods)
            def _chg(panel, partner):
                if partner not in panel.columns:
                    return float("nan"), float("nan"), None
                s = panel[partner]
                pre = s.reindex(wins["pre"]).dropna()
                post = s.reindex(wins["shock"]).dropna()
                if len(pre) == 0 or len(post) == 0:
                    return float("nan"), float("nan"), None
                return float(pre.mean()), float(post.mean()), post.index[-1]
            imp_pre, imp_post, imp_last = _chg(imp, "CAN")
            exp_pre, exp_post, exp_last = _chg(exp, china)
            flag = "no_partner_data"
            if imp_last is not None:
                mirror_gain = (imp_post - imp_pre) * len(wins["shock"])
                flag = "consistent" if mirror_gain >= 0.5 * gain else "unmatched_by_partner_imports"
            if exp_last is not None and exp_post > 2 * max(exp_pre, 1e-9):
                flag = "re_export_to_china_rose"
            rows.append({"product": product, "destination": dest, "canada_reported_gain_t": gain,
                         "partner_imports_from_canada_pre_mean_t": imp_pre, "partner_imports_from_canada_shock_mean_t": imp_post,
                         "partner_exports_to_china_pre_mean_t": exp_pre, "partner_exports_to_china_shock_mean_t": exp_post,
                         "partner_data_last_period": imp_last, "flag": flag})
    df = pd.DataFrame(rows)
    df.to_csv(tables_dir / "q1_transshipment_screen.csv", index=False)
    if len(df):
        for product in df["product"].unique():
            sub = df[df["product"] == product]
            numbers.add(f"q1.{product}.transshipment.flagged", sub.loc[sub["flag"].isin(["unmatched_by_partner_imports", "re_export_to_china_rose"]), "destination"].tolist(),
                        "iso3", "q1_diversion._transshipment", window="shock", counterfactual=C.HEADLINE_CF,
                        note="Top gainers whose own import data does not match the Canadian gain, or whose exports to China rose")
            numbers.add(f"q1.{product}.transshipment.no_partner_data", sub.loc[sub["flag"] == "no_partner_data", "destination"].tolist(),
                        "iso3", "q1_diversion._transshipment", window="shock")
