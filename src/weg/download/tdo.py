"""Trade Data Online (ISED): HS6 x country x province x month, domestic exports, value only.

The report is a query-string driven HTML page; one request per (HS6, province).
The exact response layout is confirmed at checkpoint 2; the cleaner parses tables
with pandas.read_html and asserts the expected columns.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from weg import config
from weg.download.base import fetch
from weg.manifest import Manifest

SOURCE = "tdo"
URL = "https://ised-isde.canada.ca/app/ixb/tdo/crtr.html"


def params_for(hs6: str, area: str, time_period: str = "24|Monthly Trends") -> dict:
    return {
        "searchType": "KS_CS",
        "productType": "HS6",
        "hSelectedCodes": f"|{hs6}",
        "naArea": area,
        "countryList": "ALL",
        "grouped": "INDIVIDUAL",
        "toFromCountry": "CDN",
        "reportType": "TE",
        "timePeriod": time_period,
        "currency": "CDN",
        "runReport": "true",
    }


def download(cfg: dict, vintage: str, manifest: Manifest, raw_root: Path | None = None) -> list[Path]:
    provinces = pd.read_csv(config.CONCORDANCE_DIR / "provinces.csv", dtype=str)
    codes = sorted({c for p in cfg["products"].values() for c in p["hs6"]})
    out = []
    for hs6 in codes:
        for _, prov in provinces.iterrows():
            out.append(
                fetch(
                    URL,
                    params=params_for(hs6, prov["tdo_area"]),
                    source=SOURCE,
                    vintage=vintage,
                    name=f"tdo_{hs6}_{prov['province_code']}.html",
                    issue=cfg["slug"],
                    release_tag=cfg["data"].get("data_release"),
                    raw_root=raw_root,
                    manifest=manifest,
                )
            )
    return out
