import pandas as pd

from weg import periods as P
from weg.analysis.reconcile import reconcile, within_tolerance


def test_best_lag_and_cif_ratio():
    idx = P.month_range("2023-01", "2024-12")
    exports = pd.Series([100.0 + (i % 5) * 10 for i in range(len(idx))], index=idx)
    # partner records each shipment one month later at 5% above FOB
    imports = pd.Series({P.shift(p, 1): v * 1.05 for p, v in exports.items()})
    r = reconcile(exports, imports, lags=[0, 1, 2])
    assert r["best_lag"] == 1
    annual = r["per_lag"][1]["annual"]
    assert abs(annual.loc["2023", "ratio"] - 1.05) < 1e-12
    checked = within_tolerance(annual, [0.95, 1.15])
    assert checked.loc["2023", "within"]
    assert not within_tolerance(annual, [0.95, 1.02]).loc["2023", "within"]
