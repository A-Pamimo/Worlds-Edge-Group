"""numbers.json writer.

Every headline number in a report comes from here. Values are rounded to a fixed
number of significant figures and keys are sorted so two runs on the same inputs
produce byte-identical files. Timestamps and git hashes go to provenance.json, never
into numbers.json, so the reproducibility test can compare bytes.
"""
from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SIG_FIGS = 6


def round_sig(x: float, sig: int = SIG_FIGS) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    return round(x, sig - int(math.floor(math.log10(abs(x)))) - 1)


class NumbersWriter:
    def __init__(self, issue: str):
        self.issue = issue
        self.entries: dict[str, dict[str, Any]] = {}

    def add(
        self,
        key: str,
        value: Any,
        unit: str,
        method: str,
        *,
        note: str | None = None,
        estimated: bool = False,
        window: str | None = None,
        counterfactual: str | None = None,
    ) -> None:
        if key in self.entries:
            raise KeyError(f"duplicate numbers.json key: {key}")
        if isinstance(value, bool):
            v: Any = value
        elif isinstance(value, (int, float)):
            v = round_sig(float(value)) if isinstance(value, float) else value
        elif isinstance(value, dict):
            v = {k: (round_sig(float(x)) if isinstance(x, float) else x) for k, x in value.items()}
        elif isinstance(value, (list, tuple)):
            v = [round_sig(float(x)) if isinstance(x, float) else x for x in value]
        else:
            v = value
        entry: dict[str, Any] = {"value": v, "unit": unit, "method": method}
        if window:
            entry["window"] = window
        if counterfactual:
            entry["counterfactual"] = counterfactual
        if estimated:
            entry["estimated"] = True
        if note:
            entry["note"] = note
        self.entries[key] = entry

    def write(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"issue": self.issue, "numbers": dict(sorted(self.entries.items()))}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_provenance(path: Path, *, issue: str, vintages: dict[str, str], extra: dict[str, Any] | None = None) -> None:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # pragma: no cover - outside a git checkout
        commit = None
    payload = {
        "issue": issue,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": commit,
        "input_vintages": dict(sorted(vintages.items())),
    }
    if extra:
        payload.update(extra)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
