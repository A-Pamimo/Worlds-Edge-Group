from weg import periods as P


def test_period_helpers():
    assert P.shift("2025-01", -1) == "2024-12"
    assert P.months_between("2019-01", "2020-03") == 14
    assert P.month_range("2025-11", "2026-01") == ["2025-11", "2025-12", "2026-01"]
    assert P.crop_year("2024-08") == "2024/25" and P.crop_year("2025-07") == "2024/25" and P.crop_year("2025-08") == "2025/26"
    assert P.in_window("2025-04", ["2025-04", "2026-02"]) and not P.in_window("2025-03", ["2025-04", "2026-02"])
