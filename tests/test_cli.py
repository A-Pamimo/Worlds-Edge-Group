import json

from weg import config
from weg.cli import load_issue_runner


def test_issue_runner_loads_and_analyze_writes_numbers(tmp_path, monkeypatch):
    slug = "2026-10-canola-china"
    cfg = config.load_issue_config(slug)
    runner = load_issue_runner(slug)
    cfg["_dir"] = str(tmp_path)
    runner.analyze(cfg)
    runner.figures(cfg)
    data = json.loads((tmp_path / "outputs" / "numbers.json").read_text())
    assert data["issue"] == slug
    assert data["numbers"]["meta.latest_period"]["value"] == cfg["data"]["latest_period"]
    assert (tmp_path / "outputs" / "provenance.json").exists()
