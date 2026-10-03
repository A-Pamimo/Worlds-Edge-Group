import numpy as np
import pandas as pd

from weg import periods as P
from weg.analysis import counterfactual as CF
from weg.analysis.seasonality import fit_trend_seasonal, seasonally_adjust


def exact_series(a=5.0, b=0.01, effects=None, start="2019-01", end="2024-12"):
    effects = effects or [0, 0.1, -0.2, 0.3, 0.0, -0.1, 0.05, 0.2, -0.3, 0.4, 0.5, -0.05]
    idx = P.month_range(start, end)
    vals = [np.exp(a + b * P.months_between(start, p) + effects[P.month_of(p) - 1]) for p in idx]
    return pd.Series(vals, index=idx)


def test_fit_recovers_exact_parameters():
    s = exact_series()
    fit = fit_trend_seasonal(s, "2019-01", "2024-12")
    assert fit is not None
    assert abs(fit.intercept - 5.0) < 1e-9
    assert abs(fit.trend - 0.01) < 1e-9
    assert np.allclose(fit.month_effects, [0, 0.1, -0.2, 0.3, 0.0, -0.1, 0.05, 0.2, -0.3, 0.4, 0.5, -0.05])
    assert fit.resid_sd < 1e-9


def test_prediction_extends_the_exact_path():
    s = exact_series()
    fit = fit_trend_seasonal(s, "2019-01", "2024-12")
    pred = fit.predict(["2025-01", "2025-06"])
    expected = exact_series(end="2025-12")
    assert abs(pred["2025-01"] - expected["2025-01"]) < 1e-6
    assert abs(pred["2025-06"] - expected["2025-06"]) < 1e-6


def test_factors_normalised_and_adjustment_flattens():
    s = exact_series(b=0.0)
    fit = fit_trend_seasonal(s, "2019-01", "2024-12")
    f = fit.factors()
    assert abs(np.log(f).mean()) < 1e-12
    sa = seasonally_adjust(s, f)
    assert sa.std() / sa.mean() < 1e-9


def test_exclusion_window_ignores_shock_years():
    s = exact_series()
    s.loc[[p for p in s.index if "2020-01" <= p <= "2021-12"]] *= 0.1
    fit_all = fit_trend_seasonal(s, "2019-01", "2024-12")
    fit_ex = fit_trend_seasonal(s, "2019-01", "2024-12", exclude=[["2020-01", "2021-12"]])
    assert abs(fit_ex.trend - 0.01) < 1e-9
    assert abs(fit_all.trend - 0.01) > 1e-4


def test_too_few_observations_returns_none():
    s = exact_series(start="2023-01", end="2024-12")
    assert fit_trend_seasonal(s, "2019-01", "2024-12", min_obs=36) is None


def test_counterfactual_a_is_prior_year():
    s = pd.Series({"2024-03": 10.0, "2024-04": 20.0})
    cf = CF.same_months_prior_year(s, ["2025-03", "2025-04", "2025-05"])
    assert cf.tolist() == [10.0, 20.0, 0.0]


def test_counterfactual_dispatch():
    s = exact_series()
    a = CF.counterfactual(s, ["2025-01"], {"name": "same_months_prior_year"})
    b = CF.counterfactual(s, ["2025-01"], {"name": "trend_seasonal", "fit_start": "2019-01", "fit_end": "2024-12"})
    assert abs(a["2025-01"] - s["2024-01"]) < 1e-12
    assert abs(b["2025-01"] - s["2024-01"] * np.exp(0.12)) < 1e-6
