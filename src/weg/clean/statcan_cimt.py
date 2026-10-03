"""CIMT bulk zip -> ca_exports parquet (schema S).

Layout (documented by users of the bulk files; confirmed on the first live zip at
checkpoint 2): a detailed CSV with columns YearMonth, HS, Country, State, Value,
Quantity, UoM (province absent for exports), plus fixed-width lookup files for
countries and units. The detailed member is detected from its header, not its name.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from weg import config
from weg.schemas import validate


@dataclass
class Layout:
    encoding: str = "latin-1"
    yearmonth: str = "YearMonth"
    hs: str = "HS"
    country: str = "Country"
    value: str = "Value"
    quantity: str = "Quantity"
    uom: str = "UoM"
    country_lookup_patterns: list[str] = field(default_factory=lambda: [r"country", r"pays"])


def _norm(col: str) -> str:
    return re.sub(r"[^a-z]", "", col.lower())


def detect_detail_member(zf: zipfile.ZipFile, layout: Layout) -> str:
    """Pick the CSV whose header carries the HS code and value columns and the longest HS codes."""
    best, best_len = None, -1
    for name in zf.namelist():
        if not name.lower().endswith(".csv"):
            continue
        with zf.open(name) as fh:
            head = fh.read(4096).decode(layout.encoding, errors="replace")
        lines = head.splitlines()
        if not lines:
            continue
        cols = [_norm(c) for c in lines[0].split(",")]
        if _norm(layout.hs) in cols and _norm(layout.value) in cols and len(lines) > 1:
            hs_idx = cols.index(_norm(layout.hs))
            first = lines[1].split(",")
            hs_len = len(first[hs_idx].strip().strip('"')) if hs_idx < len(first) else 0
            if hs_len > best_len:
                best, best_len = name, hs_len
    if best is None:
        raise ValueError("no detailed CSV member found in zip")
    return best


def read_country_lookup(zf: zipfile.ZipFile, layout: Layout) -> dict[str, str]:
    """Country code -> name from the fixed-width lookup member, if present."""
    for name in zf.namelist():
        low = name.lower()
        if any(re.search(p, low) for p in layout.country_lookup_patterns) and not low.endswith(".csv"):
            text = zf.read(name).decode(layout.encoding, errors="replace")
            out = {}
            for line in text.splitlines():
                m = re.match(r"\s*(\S+)\s+(.+?)\s*$", line)
                if m:
                    out[m.group(1)] = m.group(2)
            if out:
                return out
    return {}


def country_concordance() -> dict[str, str]:
    """StatCan country name -> ISO3 from the committed concordance."""
    df = pd.read_csv(config.CONCORDANCE_DIR / "countries.csv", dtype=str)
    return dict(zip(df["statcan_name"].str.strip().str.lower(), df["iso3"]))


def parse_zip(path: Path, vintage: str, hs6_filter: set[str] | None = None, layout: Layout | None = None,
              trade_type: str = "domestic") -> pd.DataFrame:
    layout = layout or Layout()
    with zipfile.ZipFile(path) as zf:
        member = detect_detail_member(zf, layout)
        lookup = read_country_lookup(zf, layout)
        raw = zf.read(member)
    df = pd.read_csv(io.BytesIO(raw), dtype=str, encoding=layout.encoding)
    cols = {_norm(c): c for c in df.columns}
    need = {k: cols[_norm(getattr(layout, k))] for k in ("yearmonth", "hs", "country", "value")}
    qcol = cols.get(_norm(layout.quantity))
    ucol = cols.get(_norm(layout.uom))
    hs = df[need["hs"]].str.replace(r"\D", "", regex=True)
    out = pd.DataFrame(
        {
            "period": df[need["yearmonth"]].str.replace(r"\D", "", regex=True).str.slice(0, 6).str.replace(r"^(\d{4})(\d{2})$", r"\1-\2", regex=True),
            "hs8": hs.str.slice(0, 8).str.ljust(8, "0"),
            "hs6": hs.str.slice(0, 6),
            "country_raw": df[need["country"]].str.strip(),
            "value_cad": pd.to_numeric(df[need["value"]], errors="coerce").fillna(0.0),
            "qty": pd.to_numeric(df[qcol], errors="coerce") if qcol else float("nan"),
            "qty_unit": df[ucol].str.strip() if ucol else None,
        }
    )
    if hs6_filter:
        out = out[out["hs6"].isin(hs6_filter)].copy()
    names = out["country_raw"].map(lookup).fillna(out["country_raw"])
    iso = names.str.strip().str.lower().map(country_concordance())
    unmapped = sorted(names[iso.isna()].unique())
    if unmapped:
        # keep the raw name so nothing is silently dropped; the concordance is extended at review
        iso = iso.fillna("UNMAPPED:" + names)
    out["partner_iso3"] = iso
    out["trade_type"] = trade_type
    out["vintage"] = vintage
    out = out.drop(columns=["country_raw"])
    out = (
        out.groupby(["period", "hs6", "hs8", "partner_iso3", "trade_type", "qty_unit"], dropna=False, as_index=False)
        .agg(value_cad=("value_cad", "sum"), qty=("qty", lambda s: s.sum(min_count=1)))
    )
    out["qty_unit"] = out["qty_unit"].astype(object)
    out["vintage"] = vintage
    out = out[["period", "hs6", "hs8", "partner_iso3", "trade_type", "value_cad", "qty", "qty_unit", "vintage"]]
    out = out.sort_values(["hs8", "partner_iso3", "period"]).reset_index(drop=True)
    out.attrs["unmapped_countries"] = unmapped
    return validate(out, "ca_exports")


def parse(paths: list[Path], vintage: str, hs6_filter: set[str] | None = None, layout: Layout | None = None) -> pd.DataFrame:
    frames = [parse_zip(p, vintage, hs6_filter, layout) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    df.attrs["unmapped_countries"] = sorted({u for f in frames for u in f.attrs.get("unmapped_countries", [])})
    return validate(df.sort_values(["hs8", "partner_iso3", "period"]).reset_index(drop=True), "ca_exports")
