"""Trade Data Online HTML report -> ca_exports_province parquet (schema P).

Layout is confirmed at checkpoint 2. The parser accepts a wide table (countries as
rows, months as columns) or a long table and normalises to period x hs6 x partner x
province. Unmapped country names are kept with an UNMAPPED: prefix.
"""
from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import pandas as pd

from weg.clean.statcan_cimt import country_concordance
from weg.schemas import validate

MONTH_RE = re.compile(r"^(?P<m>[A-Za-z]{3,9})[ \-]?(?P<y>\d{4})$")
MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})


def _period(label: str) -> str | None:
    m = MONTH_RE.match(str(label).strip())
    if not m:
        return None
    mon = MONTHS.get(m.group("m").lower())
    return f"{m.group('y')}-{mon:02d}" if mon else None


def parse_html(path: Path, hs6: str, province: str, vintage: str) -> pd.DataFrame:
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    tables = pd.read_html(StringIO(html))
    candidates = [t for t in tables if any(_period(c) for c in map(str, t.columns))]
    if not candidates:
        raise ValueError(f"{path.name}: no table with month columns")
    t = max(candidates, key=len)
    country_col = t.columns[0]
    month_cols = {c: _period(str(c)) for c in t.columns if _period(str(c))}
    long = t.melt(id_vars=[country_col], value_vars=list(month_cols), var_name="col", value_name="value_cad")
    long["period"] = long["col"].map(month_cols)
    long["value_cad"] = pd.to_numeric(long["value_cad"].astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce").fillna(0.0)
    names = long[country_col].astype(str).str.strip()
    long = long[~names.str.lower().isin({"total", "sub-total", "subtotal", "all countries"})]
    names = long[country_col].astype(str).str.strip()
    iso = names.str.lower().map(country_concordance()).fillna("UNMAPPED:" + names)
    out = pd.DataFrame({
        "period": long["period"], "hs6": hs6, "partner_iso3": iso, "province": province,
        "value_cad": long["value_cad"], "vintage": vintage,
    })
    out = out.groupby(["period", "hs6", "partner_iso3", "province"], as_index=False).agg(value_cad=("value_cad", "sum"), vintage=("vintage", "first"))
    return validate(out.sort_values(["partner_iso3", "period"]).reset_index(drop=True), "ca_exports_province")
