"""Standard clean-table schemas shared by every issue.

S  ca_exports            Canadian domestic exports (StatCan CIMT), HS8/HS6 x partner x month, value + quantity
P  ca_exports_province   Canadian domestic exports by province of origin (Trade Data Online), value only
C  comtrade              Partner-reported trade (UN Comtrade), reporter x flow x HS6 x partner x month
FX fx                    Bank of Canada monthly average exchange rates
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SchemaError(ValueError):
    pass


@dataclass(frozen=True)
class Schema:
    name: str
    columns: dict[str, str]  # column -> pandas dtype family: str|int|float|bool
    key: list[str]
    nonnegative: list[str] = field(default_factory=list)


SCHEMAS: dict[str, Schema] = {
    "ca_exports": Schema(
        name="ca_exports",
        columns={
            "period": "str", "hs6": "str", "hs8": "str", "partner_iso3": "str",
            "trade_type": "str", "value_cad": "float", "qty": "float", "qty_unit": "str",
            "vintage": "str",
        },
        key=["period", "hs8", "partner_iso3", "trade_type", "qty_unit"],
        nonnegative=["value_cad", "qty"],
    ),
    "ca_exports_province": Schema(
        name="ca_exports_province",
        columns={
            "period": "str", "hs6": "str", "partner_iso3": "str", "province": "str",
            "value_cad": "float", "vintage": "str",
        },
        key=["period", "hs6", "partner_iso3", "province"],
        nonnegative=["value_cad"],
    ),
    "comtrade": Schema(
        name="comtrade",
        columns={
            "period": "str", "reporter_iso3": "str", "flow": "str", "hs6": "str",
            "partner_iso3": "str", "value_usd": "float", "net_wgt_kg": "float", "qty": "float",
            "qty_unit": "str", "is_aggregate": "bool", "dataset_code": "str", "vintage": "str",
        },
        key=["period", "reporter_iso3", "flow", "hs6", "partner_iso3"],
        nonnegative=["value_usd", "net_wgt_kg"],
    ),
    "fx": Schema(
        name="fx",
        columns={"period": "str", "pair": "str", "rate": "float", "vintage": "str"},
        key=["period", "pair"],
        nonnegative=["rate"],
    ),
}

_FAMILY = {
    "str": lambda s: pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s),
    "int": pd.api.types.is_integer_dtype,
    "float": lambda s: pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s),
    "bool": pd.api.types.is_bool_dtype,
}


def validate(df: pd.DataFrame, schema: Schema | str, allow_extra: bool = False) -> pd.DataFrame:
    """Raise SchemaError listing every problem found; return df unchanged when clean."""
    if isinstance(schema, str):
        schema = SCHEMAS[schema]
    problems: list[str] = []
    missing = [c for c in schema.columns if c not in df.columns]
    if missing:
        problems.append(f"missing columns: {missing}")
    if not allow_extra:
        extra = [c for c in df.columns if c not in schema.columns]
        if extra:
            problems.append(f"unexpected columns: {extra}")
    for col, family in schema.columns.items():
        if col in df.columns and not _FAMILY[family](df[col]):
            problems.append(f"column {col!r} should be {family}, got {df[col].dtype}")
    if "period" in df.columns and not missing:
        bad = df.loc[~df["period"].astype(str).str.match(PERIOD_RE), "period"].unique()[:5]
        if len(bad):
            problems.append(f"period must be YYYY-MM, e.g. {list(bad)}")
    if not missing:
        dupes = df.duplicated(subset=schema.key, keep=False)
        if dupes.any():
            sample = df.loc[dupes, schema.key].head(3).to_dict("records")
            problems.append(f"{int(dupes.sum())} duplicate rows on key {schema.key}, e.g. {sample}")
        for col in schema.nonnegative:
            if col in df.columns and (df[col] < 0).any():
                problems.append(f"negative values in {col!r}")
        for col in schema.columns:
            if col in df.columns and df[col].isna().any() and col not in ("qty", "net_wgt_kg", "qty_unit"):
                problems.append(f"nulls in {col!r}")
    if problems:
        raise SchemaError(f"schema {schema.name}: " + "; ".join(problems))
    return df
