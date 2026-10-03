import pytest

from weg.report import ReportError, render


def test_render_formats():
    n = {"a": {"value": 1234.5}, "s": {"value": -0.1234}, "c": {"value": 12_345_678.0}, "l": {"value": ["JPN", "MEX"]},
         "lab": {"value": "narrowing"}}
    t = "{{a|t}} {{a|kt}} {{s|pct}} {{s|signed_pct}} {{c|cad_m}} {{c|cad}} {{a|cad_t}} {{l|list}} {{lab}} {{a}}"
    assert render(t, n) == "1,234 t 1.2 kt -12.3% -12.3% CAD 12.3 million CAD 12,345,678 CAD 1,234/t JPN, MEX narrowing 1,234"


def test_unknown_key_and_nan_fail():
    with pytest.raises(ReportError, match="missing q9.x"):
        render("{{q9.x}}", {})
    with pytest.raises(ReportError, match="not finite"):
        render("{{a|pct}}", {"a": {"value": float("nan")}})
    with pytest.raises(ReportError, match="unknown format"):
        render("{{a|bogus}}", {"a": {"value": 1.0}})
