"""Synthetic clean dataset generator shared by pipeline tests (no network, deterministic)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from weg import periods as P

PRODUCTS = {
    "120510": ("12051000", 400.0, 650.0),
    "151411": ("15141100", 60.0, 1500.0),
    "230641": ("23064100", 150.0, 350.0),
    "071310": ("07131000", 80.0, 500.0),
}
PARTNERS = {"CHN": 1.0, "JPN": 0.3, "MEX": 0.2, "ARE": 0.1, "PAK": 0.15, "BGD": 0.05}
PROVINCES = {"SK": 0.5, "AB": 0.3, "MB": 0.2}


def build(clean_dir: Path, first="2019-01", last="2026-07", shock_from="2025-04") -> None:
    rng = np.random.default_rng(7)
    periods = P.month_range(first, last)
    ca_rows, prov_rows, ct_rows = [], [], []
    for hs6, (hs8, base, price0) in PRODUCTS.items():
        for partner, w in PARTNERS.items():
            for i, p in enumerate(periods):
                month = P.month_of(p)
                seasonal = 1 + 0.3 * np.cos((month - 11) * 2 * np.pi / 12)
                qty_t = base * w * seasonal * (1 + 0.03 * (i / 12))
                if p >= shock_from:
                    qty_t *= 0.15 if partner == "CHN" else 1.8
                price = price0 * (1 + 0.1 * np.sin(i / 9)) * (0.92 if (p >= shock_from and partner != "CHN") else 1.0)
                price *= 1 + rng.normal(0, 0.01)
                qty_kg = round(qty_t * 1000)
                value = qty_t * price
                ca_rows.append({"period": p, "hs6": hs6, "hs8": hs8, "partner_iso3": partner, "trade_type": "domestic",
                                "value_cad": value, "qty": float(qty_kg), "qty_unit": "KGM", "vintage": "synthetic"})
                for prov, pw in PROVINCES.items():
                    prov_rows.append({"period": p, "hs6": hs6, "partner_iso3": partner, "province": prov,
                                      "value_cad": value * pw, "vintage": "synthetic"})
                # China's own imports (CIF +6%, one month later), plus competitors
                if partner == "CHN":
                    nxt = P.shift(p, 1)
                    if nxt <= last:
                        ct_rows.append({"period": nxt, "reporter_iso3": "CHN", "flow": "M", "hs6": hs6, "partner_iso3": "CAN",
                                        "value_usd": value * 1.06 / 1.35, "net_wgt_kg": float(qty_kg), "qty": float(qty_kg),
                                        "qty_unit": "kg", "is_aggregate": False, "dataset_code": "x", "vintage": "synthetic"})
                        for comp, cw in (("AUS", 0.4), ("RUS", 0.2)):
                            q = base * cw * seasonal * 1000 * (2.5 if p >= shock_from else 1.0)
                            ct_rows.append({"period": nxt, "reporter_iso3": "CHN", "flow": "M", "hs6": hs6, "partner_iso3": comp,
                                            "value_usd": q / 1000 * price0 / 1.35, "net_wgt_kg": q, "qty": q, "qty_unit": "kg",
                                            "is_aggregate": False, "dataset_code": "x", "vintage": "synthetic"})
                if partner == "JPN":
                    nxt = P.shift(p, 1)
                    if nxt <= last:
                        ct_rows.append({"period": nxt, "reporter_iso3": "JPN", "flow": "M", "hs6": hs6, "partner_iso3": "CAN",
                                        "value_usd": value * 1.06 / 1.35, "net_wgt_kg": float(qty_kg), "qty": float(qty_kg),
                                        "qty_unit": "kg", "is_aggregate": False, "dataset_code": "x", "vintage": "synthetic"})
    clean_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ca_rows).to_parquet(clean_dir / "ca_exports.parquet", index=False)
    pd.DataFrame(prov_rows).to_parquet(clean_dir / "ca_exports_province.parquet", index=False)
    pd.DataFrame(ct_rows).to_parquet(clean_dir / "comtrade_imports.parquet", index=False)
    pd.DataFrame({"period": periods, "pair": "FXMUSDCAD", "rate": 1.35, "vintage": "synthetic"}).to_parquet(clean_dir / "fx_monthly.parquet", index=False)
