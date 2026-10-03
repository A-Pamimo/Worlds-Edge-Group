"""Issue 1 pipeline entry points, called by `python -m weg <stage> --issue 2026-10-canola-china`.

Stages are filled in checkpoint by checkpoint. Each stage must be a pure function of
the issue config and the data on disk so `make all` is reproducible.
"""
from __future__ import annotations

from pathlib import Path

from weg.numbers import NumbersWriter, write_provenance

STEPS_IMPLEMENTED: list[str] = []


def _outputs(cfg: dict) -> Path:
    out = Path(cfg["_dir"]) / "outputs"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    return out


def download(cfg: dict, vintage: str = "pinned") -> None:
    raise NotImplementedError("download stage arrives in checkpoint 2 (StatCan, BoC) and 3 (Comtrade)")


def clean(cfg: dict, vintage: str = "pinned") -> None:
    raise NotImplementedError("clean stage arrives in checkpoint 2")


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
