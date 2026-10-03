"""Issue 1 pipeline entry points, called by `python -m weg <stage> --issue 2026-10-canola-china`.

Each stage is a function of the issue config and the files on disk, so `make all`
is reproducible. Stages are filled in checkpoint by checkpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from weg import config
from weg.clean import boc as clean_boc
from weg.clean import comtrade as clean_comtrade
from weg.clean import statcan_cimt as clean_cimt
from weg.clean import tdo as clean_tdo
from weg.download import boc, cgc, comtrade, statcan_cimt, tdo
from weg.download import vintage as V
from weg.manifest import Manifest
from weg.numbers import NumbersWriter, write_provenance

STEPS_IMPLEMENTED: list[str] = ["download", "clean"]


def _outputs(cfg: dict) -> Path:
    out = Path(cfg["_dir"]) / "outputs"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    return out


def _manifest() -> Manifest:
    return Manifest(config.MANIFEST_PATH, root=config.ROOT)


def _hs6(cfg: dict) -> set[str]:
    return {c for p in cfg["products"].values() for c in p["hs6"]}


def _raw_files(manifest: Manifest, source: str, vintage: str, issue: str) -> list[Path]:
    rows = [r for r in manifest.rows.values() if r.source == source and r.vintage == vintage and r.issue == issue]
    return [config.ROOT / r.raw_path for r in sorted(rows, key=lambda r: r.raw_path)]


def download(cfg: dict, vintage: str = "pinned") -> None:
    m = _manifest()
    resolved = {}
    for source, fn in (("boc", boc.download), ("statcan_cimt", statcan_cimt.download), ("cgc", cgc.download),
                       ("tdo", tdo.download), ("comtrade", comtrade.download)):
        v = V.resolve(cfg, source, vintage, m)
        resolved[source] = v
        print(f"[weg] download {source} vintage={v}")
        fn(cfg, vintage=v, manifest=m)
    print("[weg] vintages used (pin these in config.yaml data.vintages):")
    print(json.dumps(resolved, indent=2))


def clean(cfg: dict, vintage: str = "pinned") -> None:
    m = _manifest()
    issue = cfg["slug"]
    config.DATA_CLEAN.mkdir(parents=True, exist_ok=True)
    report = {}

    v = V.resolve(cfg, "boc", vintage, m)
    fx = clean_boc.parse(_raw_files(m, "boc", v, issue)[0], v)
    fx.to_parquet(config.DATA_CLEAN / "fx_monthly.parquet", index=False)
    report["fx"] = {"rows": len(fx), "periods": [fx.period.min(), fx.period.max()], "vintage": v}

    v = V.resolve(cfg, "statcan_cimt", vintage, m)
    ca = clean_cimt.parse(_raw_files(m, "statcan_cimt", v, issue), v, hs6_filter=_hs6(cfg))
    ca.to_parquet(config.DATA_CLEAN / "ca_exports.parquet", index=False)
    report["ca_exports"] = {"rows": len(ca), "periods": [ca.period.min(), ca.period.max()], "vintage": v,
                            "unmapped_countries": ca.attrs.get("unmapped_countries", [])}

    v = V.resolve(cfg, "tdo", vintage, m)
    frames = []
    for path in _raw_files(m, "tdo", v, issue):
        _, hs6, prov = path.stem.split("_")
        frames.append(clean_tdo.parse_html(path, hs6, prov, v))
    if frames:
        prov_df = pd.concat(frames, ignore_index=True)
        prov_df.to_parquet(config.DATA_CLEAN / "ca_exports_province.parquet", index=False)
        report["ca_exports_province"] = {"rows": len(prov_df), "periods": [prov_df.period.min(), prov_df.period.max()], "vintage": v}

    v = V.resolve(cfg, "comtrade", vintage, m)
    files = [p for p in _raw_files(m, "comtrade", v, issue) if p.name.startswith("C_M_HS")]
    ct = clean_comtrade.parse(files, v)
    ct.to_parquet(config.DATA_CLEAN / "comtrade_imports.parquet", index=False)
    report["comtrade_imports"] = {"rows": len(ct), "reporters": sorted(ct.reporter_iso3.unique()), "vintage": v}

    (_outputs(cfg) / "tables" / "clean_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


def analyze(cfg: dict, vintage: str = "pinned") -> None:
    out = _outputs(cfg)
    numbers = NumbersWriter(cfg["slug"])
    numbers.add(
        "meta.latest_period", cfg["data"]["latest_period"], "YYYY-MM",
        "config.data.latest_period", note="Latest StatCan reference month used",
    )
    numbers.add("meta.steps_implemented", list(STEPS_IMPLEMENTED), "list", "analysis/run.py")
    numbers.write(out / "numbers.json")
    write_provenance(out / "provenance.json", issue=cfg["slug"], vintages={k: str(v) for k, v in cfg["data"]["vintages"].items()})


def figures(cfg: dict, vintage: str = "pinned") -> None:
    _outputs(cfg)
    # figure list arrives with checkpoint 5


def archive(cfg: dict, vintage: str = "pinned") -> None:
    raise NotImplementedError("archive stage arrives in checkpoint 10")
