"""Statistics Canada CIMT bulk zips (71-607-X2021004): domestic exports by HS8 x country x month."""
from __future__ import annotations

from pathlib import Path

from weg.download.base import fetch
from weg.manifest import Manifest

SOURCE = "statcan_cimt"
URL = "https://www150.statcan.gc.ca/n1/pub/71-607-x/2021004/zip/CIMT-CICM_{flow}_{year}.zip"
FLOWS = {"domestic": "Dom_Exp", "total": "Tot_Exp", "imports": "Imp"}


def download(cfg: dict, vintage: str, manifest: Manifest, raw_root: Path | None = None, flow: str = "domestic") -> list[Path]:
    first_year = int(cfg["data"]["first_period"][:4])
    last_year = int(cfg["data"]["latest_period"][:4])
    out = []
    for year in range(first_year, last_year + 1):
        url = URL.format(flow=FLOWS[flow], year=year)
        out.append(
            fetch(
                url,
                source=SOURCE,
                vintage=vintage,
                name=f"CIMT-CICM_{FLOWS[flow]}_{year}.zip",
                issue=cfg["slug"],
                release_tag=cfg["data"].get("data_release"),
                raw_root=raw_root,
                manifest=manifest,
            )
        )
    return out
