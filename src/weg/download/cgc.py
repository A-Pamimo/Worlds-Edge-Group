"""Canadian Grain Commission: monthly exports of Canadian grain by destination (tonnes)."""
from __future__ import annotations

from pathlib import Path

from weg.download.base import fetch
from weg.manifest import Manifest

SOURCE = "cgc"
URL = "https://www.grainscanada.gc.ca/en/grain-research/statistics/exports-grain-wheat-flour/csv/exports.csv"


def download(cfg: dict, vintage: str, manifest: Manifest, raw_root: Path | None = None) -> Path:
    return fetch(
        URL,
        source=SOURCE,
        vintage=vintage,
        name="exports.csv",
        issue=cfg["slug"],
        release_tag=cfg["data"].get("data_release"),
        raw_root=raw_root,
        manifest=manifest,
    )
