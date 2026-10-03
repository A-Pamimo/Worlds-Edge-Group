"""Comtrade JSON -> comtrade parquet (schema C)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from weg.schemas import validate

WORLD = "WLD"


def parse_file(path: Path, vintage: str) -> pd.DataFrame:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    data = payload.get("data", [])
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # breakdown guards: classic mode must give one row per reporter x partner x cmd x period
    for col, expected in (("partner2Code", 0), ("motCode", 0)):
        bad = df[col].astype(int) != expected
        if bad.any():
            raise ValueError(f"{path.name}: {int(bad.sum())} rows with {col} != {expected}")
    if (df["customsCode"].astype(str) != "C00").any():
        raise ValueError(f"{path.name}: rows with customsCode != C00")
    out = pd.DataFrame(
        {
            "period": df["refYear"].astype(int).astype(str) + "-" + df["refMonth"].astype(int).map("{:02d}".format),
            "reporter_iso3": df["reporterISO"].astype(str),
            "flow": df["flowCode"].astype(str),
            "hs6": df["cmdCode"].astype(str).str.zfill(6),
            "partner_iso3": df["partnerISO"].astype(str).replace({"W00": WORLD}),
            "value_usd": pd.to_numeric(df["primaryValue"], errors="coerce").fillna(0.0),
            "net_wgt_kg": pd.to_numeric(df.get("netWgt"), errors="coerce"),
            "qty": pd.to_numeric(df.get("qty"), errors="coerce"),
            "qty_unit": df.get("qtyUnitAbbr", pd.Series([None] * len(df))).astype(object),
            "is_aggregate": df.get("isAggregate", pd.Series([False] * len(df))).astype(bool),
            "dataset_code": df.get("datasetCode", pd.Series([""] * len(df))).astype(str),
            "vintage": vintage,
        }
    )
    return out


def parse(paths: list[Path], vintage: str) -> pd.DataFrame:
    frames = [parse_file(p, vintage) for p in paths]
    frames = [f for f in frames if len(f)]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=[])
    df = df.sort_values(["reporter_iso3", "flow", "hs6", "partner_iso3", "period"]).reset_index(drop=True)
    return validate(df, "comtrade")
