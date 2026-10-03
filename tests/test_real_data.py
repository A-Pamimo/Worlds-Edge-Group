"""Tests that run only when real clean data exists (skipped on fixtures-only CI).

1. Reconciliation: Canada-reported exports to China vs China-reported imports from Canada,
   annual ratios within the per-product tolerance band in config.yaml.
2. Reproducibility: re-running the analysis from data/clean reproduces the committed
   outputs/numbers.json byte for byte.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from weg import config
from weg.analysis.reconcile import reconcile, within_tolerance
from weg.cli import load_issue_runner

SLUG = "2026-10-canola-china"
CLEAN = config.DATA_CLEAN
HAVE_DATA = all((CLEAN / f).exists() for f in ("ca_exports.parquet", "comtrade_imports.parquet", "fx_monthly.parquet"))
pytestmark = pytest.mark.skipif(not HAVE_DATA, reason="no clean data in data/clean (run make download clean)")


def test_reconciliation_within_tolerance():
    cfg = config.load_issue_config(SLUG)
    ca = pd.read_parquet(CLEAN / "ca_exports.parquet")
    ct = pd.read_parquet(CLEAN / "comtrade_imports.parquet")
    china = cfg["markets"]["china"]
    failures = []
    table = []
    for product, spec in cfg["products"].items():
        e = ca[(ca.hs6.isin(spec["hs6"])) & (ca.partner_iso3 == china) & (ca.trade_type == "domestic")].groupby("period")["qty"].sum() / 1000
        i = ct[(ct.reporter_iso3 == china) & (ct.flow == "M") & (ct.hs6.isin(spec["hs6"])) & (ct.partner_iso3 == "CAN")].groupby("period")["net_wgt_kg"].sum() / 1000
        if e.empty or i.empty:
            failures.append(f"{product}: no data on one side")
            continue
        r = reconcile(e, i, lags=cfg["reconciliation"]["lag_months"])
        annual = within_tolerance(r["per_lag"][r["best_lag"]]["annual"], cfg["reconciliation"]["tolerance"][product], min_exports=1000.0)
        annual["product"] = product
        annual["best_lag"] = r["best_lag"]
        table.append(annual)
        complete_years = [y for y in annual.index if y < cfg["data"]["latest_period"][:4]]
        bad = annual.loc[complete_years][~annual.loc[complete_years, "within"]]
        if len(bad):
            failures.append(f"{product} (lag {r['best_lag']}): " + ", ".join(f"{y}={row.ratio:.2f}" for y, row in bad.iterrows()))
    out = config.ISSUES_DIR / SLUG / "outputs" / "tables" / "reconciliation_china.csv"
    pd.concat(table).to_csv(out)
    assert not failures, "partner/Canada annual ratios outside tolerance: " + "; ".join(failures)


def test_numbers_json_reproduces(tmp_path):
    cfg = config.load_issue_config(SLUG)
    committed = Path(cfg["_dir"]) / "outputs" / "numbers.json"
    if not committed.exists():
        pytest.skip("no committed numbers.json yet")
    cfg["_dir"] = str(tmp_path)
    load_issue_runner(SLUG).analyze(cfg)
    fresh = (tmp_path / "outputs" / "numbers.json").read_bytes()
    assert fresh == committed.read_bytes(), "numbers.json differs from the committed version"
    assert json.loads(fresh)["issue"] == SLUG
