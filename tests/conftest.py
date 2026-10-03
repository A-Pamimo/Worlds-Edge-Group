"""Synthetic fixtures. No network, no real data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def month_range(start: str, end: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]


@pytest.fixture
def periods() -> list[str]:
    return month_range("2019-01", "2026-07")


@pytest.fixture
def ca_exports(periods) -> pd.DataFrame:
    """Two products, three partners, deterministic seasonal pattern with a known break."""
    rng = np.random.default_rng(0)
    rows = []
    for hs8, hs6 in (("12051000", "120510"), ("23064100", "230641")):
        for partner, base in (("CHN", 400.0), ("JPN", 120.0), ("MEX", 60.0)):
            for i, p in enumerate(periods):
                month = int(p[5:])
                seasonal = 1 + 0.3 * np.cos((month - 11) * 2 * np.pi / 12)  # peak in Nov
                qty = base * seasonal * (1 + 0.02 * (i / 12)) * 1000.0
                if partner == "CHN" and p >= "2025-04":
                    qty *= 0.2
                if partner in ("JPN", "MEX") and p >= "2025-04":
                    qty *= 1.6
                price = 650.0 + 20 * np.sin(i / 7) + rng.normal(0, 3)
                rows.append(
                    {
                        "period": p, "hs6": hs6, "hs8": hs8, "partner_iso3": partner,
                        "trade_type": "domestic", "value_cad": qty / 1000 * price, "qty": qty,
                        "qty_unit": "KGM", "vintage": "test",
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def fx(periods) -> pd.DataFrame:
    return pd.DataFrame(
        {"period": periods, "pair": "FXMUSDCAD", "rate": 1.35, "vintage": "test"}
    )
