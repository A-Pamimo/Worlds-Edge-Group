import numpy as np
import pandas as pd

from weg.analysis import unitvalue as UV


def test_unit_value_per_tonne():
    v = pd.Series([1000.0, 0.0, 500.0])
    q = pd.Series([2000.0, 0.0, 0.0])
    uv = UV.unit_value(v, q)
    assert uv[0] == 500.0 and np.isnan(uv[1]) and np.isnan(uv[2])


def test_usd_to_cad_requires_rates(fx):
    df = pd.DataFrame({"period": ["2019-01", "2019-02"], "value_usd": [10.0, 20.0]})
    out = UV.usd_to_cad(df, fx)
    assert out["value_cad"].tolist() == [13.5, 27.0]
    bad = pd.DataFrame({"period": ["2030-01"], "value_usd": [1.0]})
    try:
        UV.usd_to_cad(bad, fx)
    except ValueError as e:
        assert "2030-01" in str(e)
    else:
        raise AssertionError


def test_price_change_with_and_without_factors():
    uv = pd.Series({"2024-01": 100.0, "2024-02": 110.0, "2024-03": 90.0, "2025-01": 80.0, "2025-02": 88.0})
    r = UV.price_change(uv, ["2024-01", "2024-03"], ["2025-01", "2025-02"])
    assert r["pre_mean"] == 100.0 and r["post_mean"] == 84.0 and abs(r["pct_change"] + 0.16) < 1e-12
    factors = pd.Series(1.0, index=range(1, 13))
    factors[2] = 1.1
    r2 = UV.price_change(uv, ["2024-01", "2024-03"], ["2025-01", "2025-02"], factors)
    assert abs(r2["post_mean"] - (80 + 80) / 2) < 1e-12
    r3 = UV.price_change(uv, ["2024-01", "2024-03"], ["2025-01", "2025-02"], min_pre_months=4)
    assert np.isnan(r3["pct_change"]) and r3["n_pre"] == 3


def test_gap_trend_classification():
    narrowing = pd.Series(np.linspace(100, 10, 12), index=[f"2025-{m:02d}" for m in range(1, 13)])
    assert UV.gap_trend(narrowing)["classification"] == "narrowing"
    widening = pd.Series(np.linspace(-10, -100, 12), index=narrowing.index)
    assert UV.gap_trend(widening)["classification"] == "widening"
    rng = np.random.default_rng(1)
    stable = pd.Series(50 + rng.normal(0, 1, 12), index=narrowing.index)
    assert UV.gap_trend(stable)["classification"] == "stable"
    assert UV.gap_trend(stable.head(3))["classification"] == "insufficient"
