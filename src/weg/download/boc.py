"""Bank of Canada Valet API: monthly average exchange rates."""
from __future__ import annotations

from pathlib import Path

from weg.download.base import fetch
from weg.manifest import Manifest

BASE = "https://www.bankofcanada.ca/valet/observations/{series}/json"
SOURCE = "boc"


def download(cfg: dict, vintage: str, manifest: Manifest, raw_root: Path | None = None) -> Path:
    pairs = list(cfg["fx"]["pairs"])
    url = BASE.format(series=",".join(pairs))
    params = {"start_date": f"{cfg['data']['first_period']}-01"}
    return fetch(
        url,
        params=params,
        source=SOURCE,
        vintage=vintage,
        name=f"valet_{'_'.join(pairs)}.json",
        issue=cfg["slug"],
        release_tag=cfg["data"].get("data_release"),
        raw_root=raw_root,
        manifest=manifest,
    )
