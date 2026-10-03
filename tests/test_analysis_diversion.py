import pandas as pd

from weg.analysis.diversion import diversion


def test_hand_computed_two_months():
    idx = ["2025-04", "2025-05"]
    actual = pd.DataFrame({"CHN": [20.0, 10.0], "JPN": [50.0, 70.0], "MEX": [30.0, 20.0]}, index=idx)
    cf = pd.DataFrame({"CHN": [100.0, 100.0], "JPN": [40.0, 40.0], "MEX": [35.0, 35.0]}, index=idx)
    r = diversion(actual, cf, "CHN", ["2025-04", "2025-05"])
    # loss: 80, 90 -> 170
    assert r.loss.tolist() == [80.0, 90.0]
    assert r.loss_total == 170.0
    # gains: JPN +10, +30 ; MEX -5, -15 -> positive 10, 30 ; matched 10, 30 ; never 70, 60
    assert r.positive_gain.tolist() == [10.0, 30.0]
    assert r.matched.tolist() == [10.0, 30.0]
    assert r.never_resold.tolist() == [70.0, 60.0]
    assert abs(r.reappeared_share_monthly - 40 / 170) < 1e-12
    assert abs(r.reappeared_share_period - 40 / 170) < 1e-12
    assert r.net_gain_total == 20.0
    assert r.ranking.iloc[0]["destination"] == "JPN"
    assert r.ranking.iloc[0]["share_of_positive_gain"] == 1.0
    assert r.world_actual_total == 200.0 and r.world_cf_total == 350.0


def test_window_filters_and_no_loss_gives_nan():
    idx = ["2025-03", "2025-04"]
    actual = pd.DataFrame({"CHN": [100.0, 120.0], "JPN": [1.0, 1.0]}, index=idx)
    cf = pd.DataFrame({"CHN": [100.0, 100.0], "JPN": [1.0, 1.0]}, index=idx)
    r = diversion(actual, cf, "CHN", ["2025-04", "2025-04"])
    assert r.loss_total == 0.0
    assert r.reappeared_share_monthly != r.reappeared_share_monthly  # NaN
