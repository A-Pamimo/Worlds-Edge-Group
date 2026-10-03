"""Vintage resolution shared by all downloaders and cleaners.

`make download VINTAGE=latest` stamps today's UTC date as the vintage of every file it
fetches. `make download` (pinned) uses the vintage in the issue config; if none is
pinned yet it falls back to the newest vintage already recorded in the manifest for
that source, so a first run is smooth and the pin is an explicit config edit after review.
"""
from __future__ import annotations

from datetime import datetime, timezone

from weg.manifest import Manifest


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve(cfg: dict, source: str, vintage_arg: str, manifest: Manifest) -> str:
    if vintage_arg == "latest":
        return today_utc()
    if vintage_arg not in ("pinned", None):
        return vintage_arg
    pinned = (cfg.get("data", {}).get("vintages") or {}).get(source)
    if pinned:
        return str(pinned)
    known = sorted({r.vintage for r in manifest.rows.values() if r.source == source})
    if known:
        print(f"[weg] {source}: no pinned vintage in config.yaml, using newest recorded {known[-1]}")
        return known[-1]
    raise RuntimeError(
        f"No vintage for source {source!r}: pin data.vintages.{source} in config.yaml "
        f"or run `make download VINTAGE=latest`."
    )
