import json

import pytest

from weg.numbers import NumbersWriter, round_sig


def test_round_sig():
    assert round_sig(123456789.0) == 123457000.0
    assert round_sig(0.000123456789) == 0.000123457
    assert round_sig(0.0) == 0.0


def test_writer_is_deterministic(tmp_path):
    def build():
        w = NumbersWriter("t")
        w.add("b.cost", 1234567.891, "CAD", "m", window="shock", counterfactual="A")
        w.add("a.share", 0.123456789, "share", "m", estimated=True, note="n")
        w.add("c.list", [1.23456789, 2.0], "t", "m")
        w.add("d.flag", True, "bool", "m")
        return w

    p1, p2 = tmp_path / "1.json", tmp_path / "2.json"
    build().write(p1)
    build().write(p2)
    assert p1.read_bytes() == p2.read_bytes()
    data = json.loads(p1.read_text())
    assert list(data["numbers"]) == ["a.share", "b.cost", "c.list", "d.flag"]
    assert data["numbers"]["b.cost"]["value"] == 1234570.0
    assert data["numbers"]["a.share"]["estimated"] is True
    assert "generated" not in p1.read_text()


def test_duplicate_key_rejected():
    w = NumbersWriter("t")
    w.add("x", 1, "u", "m")
    with pytest.raises(KeyError):
        w.add("x", 2, "u", "m")
