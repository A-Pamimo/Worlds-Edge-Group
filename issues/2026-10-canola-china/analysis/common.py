"""Issue 1 helpers: load clean tables and build period x destination panels."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from weg import config
from weg import periods as P
from weg.analysis.counterfactual import counterfactual, same_months_prior_year
from weg.analysis.seasonality import seasonal_factors

TONNE_KG = 1000.0
CF_ORDER = ["A", "B", "B_prime"]
HEADLINE_CF = "B"


@dataclass
class Tables:
    ca: pd.DataFrame
    prov: pd.DataFrame | None
    ct: pd.DataFrame
    fx: pd.DataFrame


def load_tables(clean_dir: Path | None = None) -> Tables:
    d = clean_dir or config.DATA_CLEAN
    needed = {"ca": d / "ca_exports.parquet", "ct": d / "comtrade_imports.parquet", "fx": d / "fx_monthly.parquet"}
    missing = [str(p) for p in needed.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"clean tables missing, run `make download clean` first: {missing}")
    prov_path = d / "ca_exports_province.parquet"
    return Tables(
        ca=pd.read_parquet(needed["ca"]),
        prov=pd.read_parquet(prov_path) if prov_path.exists() else None,
        ct=pd.read_parquet(needed["ct"]),
        fx=pd.read_parquet(needed["fx"]),
    )


def all_periods(cfg: dict) -> list[str]:
    return P.month_range(cfg["data"]["first_period"], cfg["data"]["latest_period"])


def window_periods(cfg: dict, product: str) -> dict[str, list[str] | None]:
    w = cfg["windows"][product]
    out = {"pre": P.month_range(*w["pre"]), "shock": P.month_range(*w["shock"])}
    out["relief"] = P.month_range(*w["relief"]) if w.get("relief") else None
    return out


def product_panel(ca: pd.DataFrame, hs6: list[str], measure: str, periods: list[str], trade_type: str = "domestic") -> pd.DataFrame:
    """period x partner_iso3 panel of tonnes (measure='qty') or CAD (measure='value_cad')."""
    df = ca[(ca["hs6"].isin(hs6)) & (ca["trade_type"] == trade_type)]
    if measure == "qty":
        units = set(df["qty_unit"].dropna().unique())
        if units - {"KGM"}:
            raise ValueError(f"unexpected quantity units for {hs6}: {units}")
        vals = df.assign(v=df["qty"].fillna(0.0) / TONNE_KG)
    else:
        vals = df.assign(v=df[measure])
    panel = vals.pivot_table(index="period", columns="partner_iso3", values="v", aggfunc="sum", fill_value=0.0)
    panel = panel.reindex(periods).fillna(0.0)
    panel = panel.loc[:, (panel.sum(axis=0) > 0)]
    panel.columns.name = None
    return panel


def comtrade_panel(ct: pd.DataFrame, reporter: str, flow: str, hs6: list[str], measure: str, periods: list[str]) -> pd.DataFrame:
    df = ct[(ct["reporter_iso3"] == reporter) & (ct["flow"] == flow) & (ct["hs6"].isin(hs6)) & (ct["partner_iso3"] != "WLD")]
    col = "net_wgt_kg" if measure == "qty" else measure
    vals = df.assign(v=df[col].fillna(0.0) / (TONNE_KG if measure == "qty" else 1.0))
    panel = vals.pivot_table(index="period", columns="partner_iso3", values="v", aggfunc="sum", fill_value=0.0)
    panel = panel.reindex([p for p in periods if p in set(df["period"])]).fillna(0.0)
    panel.columns.name = None
    return panel


def cf_specs(cfg: dict) -> dict[str, dict]:
    return {k: dict(v) for k, v in cfg["counterfactuals"].items()}


def cf_panel(panel: pd.DataFrame, periods: list[str], spec: dict, min_obs: int) -> pd.DataFrame:
    """Counterfactual for every column; columns that cannot be fit fall back to A."""
    out = {}
    for col in panel.columns:
        cf = counterfactual(panel[col], periods, spec, min_obs)
        out[col] = cf if cf is not None else same_months_prior_year(panel[col], periods)
    return pd.DataFrame(out, index=list(periods))


def factor_lookup(panel: pd.DataFrame, cfg: dict) -> dict[str, pd.Series]:
    """Month factors per column, falling back to the all-destination series."""
    specB = cfg["counterfactuals"]["B"]
    min_obs = int(cfg["seasonality"]["min_nonzero_months"])
    fallback = seasonal_factors(panel.sum(axis=1), specB["fit_start"], specB["fit_end"], min_obs=min_obs)
    if fallback is None:
        fallback = pd.Series(1.0, index=range(1, 13))
    out = {}
    for col in panel.columns:
        f = seasonal_factors(panel[col], specB["fit_start"], specB["fit_end"], min_obs=min_obs)
        out[col] = f if f is not None else fallback
    out["__fallback__"] = fallback
    return out


def unit_value_panel(value: pd.DataFrame, qty: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in value.columns if c in qty.columns]
    q = qty[cols].where(qty[cols] > 0)
    return value[cols] / q
