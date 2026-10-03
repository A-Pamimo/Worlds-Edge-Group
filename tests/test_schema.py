import pytest

from weg.schemas import SchemaError, validate


def test_fixture_is_valid(ca_exports, fx):
    validate(ca_exports, "ca_exports")
    validate(fx, "fx")


def test_duplicate_key_fails(ca_exports):
    import pandas as pd

    df = pd.concat([ca_exports, ca_exports.iloc[[0]]], ignore_index=True)
    with pytest.raises(SchemaError, match="duplicate"):
        validate(df, "ca_exports")


def test_negative_quantity_fails(ca_exports):
    df = ca_exports.copy()
    df.loc[0, "qty"] = -1.0
    with pytest.raises(SchemaError, match="negative"):
        validate(df, "ca_exports")


def test_bad_period_fails(fx):
    df = fx.copy()
    df.loc[0, "period"] = "2019/01"
    with pytest.raises(SchemaError, match="YYYY-MM"):
        validate(df, "fx")


def test_missing_and_extra_columns(fx):
    with pytest.raises(SchemaError, match="missing"):
        validate(fx.drop(columns=["rate"]), "fx")
    with pytest.raises(SchemaError, match="unexpected"):
        validate(fx.assign(extra=1), "fx")
    validate(fx.assign(extra=1), "fx", allow_extra=True)
