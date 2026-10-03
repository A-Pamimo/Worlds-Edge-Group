import pytest

from weg import config
from weg.cli import load_issue_runner


def test_issue_runner_loads_and_requires_clean_data(tmp_path):
    slug = "2026-10-canola-china"
    cfg = config.load_issue_config(slug)
    runner = load_issue_runner(slug)
    cfg["_dir"] = str(tmp_path)
    with pytest.raises(FileNotFoundError, match="clean tables missing"):
        runner.analyze(cfg, clean_dir=tmp_path / "nothing")
    assert runner.figures(cfg) == []
