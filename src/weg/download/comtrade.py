"""UN Comtrade API (data/v1) monthly HS pulls with availability (getDa) vintages.

Key comes from COMTRADE_API_KEY and is sent as a header; it never appears in the
manifest or in file names. One call per reporter x flow x year (<= 12 periods), with
the HS6 code list in a single cmdCode parameter. The free tier allows ~500 calls/day
and 100k records per call; we assert the record cap was not hit.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from weg import config
from weg.download.base import fetch, http_get
from weg.manifest import Manifest

SOURCE = "comtrade"
DATA_URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"
AVAIL_URL = "https://comtradeapi.un.org/data/v1/getDa/C/M/HS"
PUBLIC_AVAIL_URL = "https://comtradeapi.un.org/public/v1/getDa/C/M/HS"
MAX_RECORDS = 100_000
SLEEP_SECONDS = 1.1


def _headers() -> dict[str, str]:
    key = config.env("COMTRADE_API_KEY", required=True)
    return {"Ocp-Apim-Subscription-Key": key}


def availability(reporter_codes: list[int], years: list[int], use_key: bool = True) -> list[dict]:
    """Return getDa rows for the reporters and years (not recorded in the manifest)."""
    rows: list[dict] = []
    url = AVAIL_URL if use_key else PUBLIC_AVAIL_URL
    headers = _headers() if use_key else None
    for year in years:
        params = {"reporterCode": ",".join(str(c) for c in reporter_codes), "period": str(year), "freqCode": "M"}
        resp = http_get(url, params=params, headers=headers)
        rows.extend(resp.json().get("data", []))
        time.sleep(SLEEP_SECONDS)
    return rows


def periods_for_year(year: int, last_period: str) -> str:
    months = [f"{year}{m:02d}" for m in range(1, 13) if f"{year}-{m:02d}" <= last_period]
    return ",".join(months)


def download_year(
    *,
    cfg: dict,
    vintage: str,
    manifest: Manifest,
    reporter_code: int,
    flow: str,
    year: int,
    cmd_codes: list[str],
    raw_root: Path | None = None,
) -> Path:
    period = periods_for_year(year, cfg["data"]["latest_period"])
    params = {
        "reporterCode": reporter_code,
        "period": period,
        "cmdCode": ",".join(cmd_codes),
        "flowCode": flow,
        "partner2Code": 0,
        "customsCode": "C00",
        "motCode": 0,
        "breakdownMode": "classic",
        "includeDesc": "true",
        "maxRecords": MAX_RECORDS,
        "format": "JSON",
    }
    name = f"C_M_HS_r{reporter_code}_f{flow}_{year}.json"
    path = fetch(
        DATA_URL,
        params=params,
        headers=_headers(),
        source=SOURCE,
        vintage=vintage,
        name=name,
        issue=cfg["slug"],
        release_tag=cfg["data"].get("data_release"),
        raw_root=raw_root,
        manifest=manifest,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    count = payload.get("count", len(payload.get("data", [])))
    if count >= MAX_RECORDS:
        raise RuntimeError(f"Comtrade record cap hit for {name}; split the query")
    time.sleep(SLEEP_SECONDS)
    return path


def download(cfg: dict, vintage: str, manifest: Manifest, raw_root: Path | None = None) -> list[Path]:
    """Pull imports for China and every candidate market, all partners, all issue HS6 codes.

    Also pulls the partner-side availability table into raw so the vintage is documented.
    """
    import pandas as pd

    countries = pd.read_csv(config.CONCORDANCE_DIR / "countries.csv", dtype=str)
    code_of = dict(zip(countries["iso3"], countries["comtrade_code"].astype(int)))
    cmd_codes = sorted({c for p in cfg["products"].values() for c in p["hs6"]})
    reporters = [cfg["markets"]["china"], *cfg["markets"]["candidates"]]
    first_year = int(cfg["data"]["first_period"][:4])
    last_year = int(cfg["data"]["latest_period"][:4])
    years = list(range(first_year, last_year + 1))

    out: list[Path] = []
    raw_root = raw_root or config.DATA_RAW
    avail_path = raw_root / SOURCE / vintage / "getDa_imports.json"
    if not avail_path.exists():
        avail_path.parent.mkdir(parents=True, exist_ok=True)
        rows = availability([code_of[r] for r in reporters], years)
        avail_path.write_text(json.dumps(rows, indent=1, sort_keys=True), encoding="utf-8")
    manifest.record(source=SOURCE, url_or_query=f"{AVAIL_URL}?reporters={','.join(reporters)}&years={years[0]}-{years[-1]}",
                    vintage=vintage, raw_path=avail_path, issue=cfg["slug"])
    out.append(avail_path)
    available = {(int(r["reporterCode"]), str(r["period"])[:4]) for r in json.loads(avail_path.read_text())}
    # imports (flow M) for China and candidate markets; exports (flow X) for candidate markets and
    # competitors so the transshipment screen and Q3 mirror checks have the other side of each flow
    plan = [(r, "M") for r in reporters] + [(r, "X") for r in cfg["markets"]["candidates"] + cfg["markets"].get("competitors", [])
                                             if r != cfg["markets"]["china"]]
    seen = set()
    for iso3, flow in plan:
        if (iso3, flow) in seen or iso3 not in code_of:
            continue
        seen.add((iso3, flow))
        rc = code_of[iso3]
        for year in years:
            if (rc, str(year)) not in available:
                continue
            out.append(download_year(cfg=cfg, vintage=vintage, manifest=manifest, reporter_code=rc, flow=flow,
                                     year=year, cmd_codes=cmd_codes, raw_root=raw_root))
    return out
