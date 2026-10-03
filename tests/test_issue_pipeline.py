"""End-to-end: synthetic clean tables -> analyze -> numbers.json + tables -> figures. Deterministic."""
import json
import sys
from pathlib import Path

import pytest

from weg import config
from weg.cli import load_issue_runner

sys.path.insert(0, str(Path(__file__).parent))
from synth import build  # noqa: E402

SLUG = "2026-10-canola-china"


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("issue")
    clean = base / "clean"
    build(clean)
    cfg = config.load_issue_config(SLUG)
    cfg["_dir"] = str(base / "issue")
    runner = load_issue_runner(SLUG)
    runner.analyze(cfg, clean_dir=clean)
    runner.figures(cfg)
    return base, cfg, runner, clean


def _numbers(base):
    return json.loads((base / "issue" / "outputs" / "numbers.json").read_text())["numbers"]


def test_headline_numbers_exist_and_are_sane(run_dir):
    base, cfg, *_ = run_dir
    n = _numbers(base)
    for product in cfg["products"]:
        for cf in ("A", "B", "B_prime"):
            k = f"q1.{product}.{cf}.shock"
            assert n[f"{k}.loss_t"]["value"] > 0
            assert 0.0 <= n[f"{k}.reappeared_share"]["value"] <= 1.0
            assert n[f"{k}.reappeared_share"]["value"] <= n[f"{k}.reappeared_share_period"]["value"] + 1e-9
            assert n[f"q4.{product}.{cf}.shock.cost_cad"]["value"] > 0
        # synthetic: China volume fell 85%, others rose 80% -> reappearance well below 100%
        assert n[f"q1.{product}.B.shock.reappeared_share"]["value"] < 1.0
        # synthetic new buyers paid 8% less -> negative price change for new buyers
        assert n[f"q2.{product}.new_buyers.shock.pct_change_sa"]["value"] < 0
        assert n[f"q5.{product}.gap.classification"]["value"] in {"narrowing", "stable", "widening", "insufficient"}
        assert n[f"q3.{product}.shock.canada_share"]["value"] < n[f"q3.{product}.pre.canada_share"]["value"]
    assert n["q5.province.available"]["value"] is True
    assert n["q4.total.B.shock.cost_cad"]["value"] > 0
    assert n["q5.province.canola_seed.SK.B.shock.lost_tonnes_estimated"]["estimated"] is True


def test_relief_only_for_products_with_relief_window(run_dir):
    base, cfg, *_ = run_dir
    n = _numbers(base)
    assert "q5.relief.canola_oil.china_volume_ratio_to_cf" not in n
    assert "q5.relief.canola_meal.china_volume_ratio_to_cf" in n
    assert "q1.canola_oil.B.relief.loss_t" not in n


def test_figures_rendered(run_dir):
    base, *_ = run_dir
    figs = sorted(p.name for p in (base / "issue" / "outputs" / "figures").iterdir())
    assert "q1_loss_reappearance.svg" in figs and "q1_loss_reappearance.png" in figs
    assert "q4_cost_by_counterfactual.svg" in figs
    assert "q5_province_cost.svg" in figs
    assert any(f.startswith("q2_unit_values_") for f in figs)
    assert any(f.startswith("china_volume_") for f in figs)


def test_rerun_is_byte_identical(run_dir, tmp_path):
    base, cfg, runner, clean = run_dir
    cfg2 = dict(cfg)
    cfg2["_dir"] = str(tmp_path / "issue2")
    runner.analyze(cfg2, clean_dir=clean)
    a = (base / "issue" / "outputs" / "numbers.json").read_bytes()
    b = (tmp_path / "issue2" / "outputs" / "numbers.json").read_bytes()
    assert a == b
