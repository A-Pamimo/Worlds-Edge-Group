import pandas as pd

from weg.analysis.concentration import concentration, hhi, top_n_share


def test_hhi_and_top_n():
    assert hhi(pd.Series([50.0, 50.0])) == 0.5
    assert abs(hhi(pd.Series([1.0, 1.0, 1.0, 1.0])) - 0.25) < 1e-12
    assert top_n_share(pd.Series([5.0, 3.0, 1.0, 1.0]), 2) == 0.8


def test_concentration_excludes_market_and_filters_window():
    panel = pd.DataFrame({"CHN": [100.0, 100.0], "JPN": [10.0, 30.0], "MEX": [10.0, 10.0]}, index=["2025-04", "2025-05"])
    c = concentration(panel, ["2025-05", "2025-05"], exclude=["CHN"], n=1)
    assert c["total"] == 40.0 and c["hhi"] == 0.625 and c["top1_share"] == 0.75 and c["n_destinations"] == 2
