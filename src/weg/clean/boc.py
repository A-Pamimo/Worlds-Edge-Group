"""Bank of Canada Valet JSON -> fx parquet (schema fx)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from weg.schemas import validate


def parse(path: Path, vintage: str) -> pd.DataFrame:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    series = list(payload["seriesDetail"].keys())
    rows = []
    for obs in payload["observations"]:
        period = obs["d"][:7]
        for s in series:
            cell = obs.get(s)
            if cell and cell.get("v") not in (None, ""):
                rows.append({"period": period, "pair": s, "rate": float(cell["v"]), "vintage": vintage})
    df = pd.DataFrame(rows).sort_values(["pair", "period"]).reset_index(drop=True)
    return validate(df, "fx")
