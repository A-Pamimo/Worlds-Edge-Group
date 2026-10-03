"""Cleaners against fixtures that mimic each source's documented layout.
Live layouts are confirmed at checkpoints 2-3; these tests pin the parser contract."""
import io
import json
import zipfile

import pandas as pd
import pytest

from weg.clean import boc, comtrade, statcan_cimt, tdo
from weg.download.base import archive_url, asset_name
from weg.manifest import Manifest


def test_boc_parse(tmp_path):
    payload = {
        "seriesDetail": {"FXMUSDCAD": {"label": "USD/CAD"}, "FXMCNYCAD": {"label": "CNY/CAD"}},
        "observations": [
            {"d": "2019-01-01", "FXMUSDCAD": {"v": "1.3300"}, "FXMCNYCAD": {"v": "0.1960"}},
            {"d": "2019-02-01", "FXMUSDCAD": {"v": "1.3200"}},
        ],
    }
    p = tmp_path / "valet.json"
    p.write_text(json.dumps(payload))
    df = boc.parse(p, "2026-10-03")
    assert len(df) == 3
    assert df.loc[(df.pair == "FXMUSDCAD") & (df.period == "2019-02"), "rate"].item() == 1.32


def _comtrade_row(**kw):
    base = dict(refYear=2025, refMonth=3, reporterISO="CHN", flowCode="M", cmdCode="120510", partnerISO="CAN",
                partner2Code=0, customsCode="C00", motCode=0, primaryValue=1000.0, netWgt=2000.0, qty=2000.0,
                qtyUnitAbbr="kg", isAggregate=False, datasetCode="2025031560")
    base.update(kw)
    return base


def test_comtrade_parse_and_guards(tmp_path):
    p = tmp_path / "C_M_HS_r156_fM_2025.json"
    p.write_text(json.dumps({"count": 3, "data": [
        _comtrade_row(), _comtrade_row(partnerISO="AUS", primaryValue=50.0),
        _comtrade_row(partnerISO="W00", primaryValue=1050.0, isAggregate=True),
    ]}))
    df = comtrade.parse([p], "v")
    assert set(df.partner_iso3) == {"CAN", "AUS", "WLD"}
    assert df.loc[df.partner_iso3 == "WLD", "is_aggregate"].item()
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"data": [_comtrade_row(motCode=1)]}))
    with pytest.raises(ValueError, match="motCode"):
        comtrade.parse_file(bad, "v")


def _cimt_zip(path, with_quantity=True):
    detail = "YearMonth,HS,Country,State,Value" + (",Quantity,UoM" if with_quantity else "") + "\n"
    rows = [
        ("201901", "12051000", "CN", "", "1000", "2000", "KGM"),
        ("201901", "12051000", "JP", "", "500", "900", "KGM"),
        ("201901", "12051000", "XX", "", "5", "10", "KGM"),
        ("201902", "23064100", "CN", "", "300", "1500", "KGM"),
        ("201902", "99010000", "CN", "", "7", "", ""),
    ]
    for r in rows:
        detail += ",".join(r if with_quantity else r[:5]) + "\n"
    summary = "YearMonth,HS,Country,Value\n201901,120510,CN,1000\n"
    lookup = "CN   China\nJP   Japan\nXX   Narnia\n"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("CIMT-CICM_Dom_Exp_2019.csv", detail)
        zf.writestr("CIMT-CICM_Dom_Exp_HS6_2019.csv", summary)
        zf.writestr("Country_Pays.txt", lookup)
        zf.writestr("Units_Unites.txt", "KGM  Kilograms\n")


def test_cimt_parse_zip(tmp_path):
    p = tmp_path / "CIMT-CICM_Dom_Exp_2019.zip"
    _cimt_zip(p)
    df = statcan_cimt.parse_zip(p, "2026-10-03", hs6_filter={"120510", "230641"})
    assert len(df) == 4
    chn = df[(df.hs8 == "12051000") & (df.partner_iso3 == "CHN")]
    assert chn.period.item() == "2019-01" and chn.value_cad.item() == 1000.0 and chn.qty.item() == 2000.0
    assert df.attrs["unmapped_countries"] == ["Narnia"]
    assert (df.partner_iso3 == "UNMAPPED:Narnia").sum() == 1
    assert "99010000" not in set(df.hs8)


def test_cimt_parse_without_quantity(tmp_path):
    p = tmp_path / "z.zip"
    _cimt_zip(p, with_quantity=False)
    df = statcan_cimt.parse_zip(p, "v", hs6_filter={"120510"})
    assert df.qty.isna().all()


def test_tdo_parse_wide_table(tmp_path):
    html = """<html><body><table><tr><th>Country</th><th>January 2025</th><th>Feb 2025</th></tr>
    <tr><td>China</td><td>1,234</td><td>0</td></tr>
    <tr><td>Japan</td><td>10</td><td>20</td></tr>
    <tr><td>Total</td><td>1,244</td><td>20</td></tr></table></body></html>"""
    p = tmp_path / "tdo_120510_SK.html"
    p.write_text(html)
    df = tdo.parse_html(p, "120510", "SK", "v")
    assert len(df) == 4
    assert df.loc[(df.partner_iso3 == "CHN") & (df.period == "2025-01"), "value_cad"].item() == 1234.0
    assert set(df.province) == {"SK"}


def test_archive_asset_naming():
    assert asset_name("data/raw/boc/2026-10-03/valet.json") == "data__raw__boc__2026-10-03__valet.json"
    assert archive_url("data/raw/x/y.zip", "issue-1-data", repo="o/r") == "https://github.com/o/r/releases/download/issue-1-data/data__raw__x__y.zip"
