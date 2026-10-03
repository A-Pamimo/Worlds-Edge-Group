"""`python -m weg <stage> --issue <slug>`: dispatch to issues/<slug>/analysis/run.py."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from weg import config

STAGES = ("download", "clean", "analyze", "figures", "archive")


def load_issue_runner(slug: str, issues_dir: Path | None = None) -> ModuleType:
    path = config.issue_dir(slug, issues_dir) / "analysis" / "run.py"
    spec = importlib.util.spec_from_file_location(f"issue_{slug.replace('-', '_')}_run", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="weg")
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--vintage", default="pinned", help="'pinned' (default) or 'latest'")
    args = parser.parse_args(argv)
    cfg = config.load_issue_config(args.issue)
    runner = load_issue_runner(args.issue)
    fn = getattr(runner, args.stage, None)
    if fn is None:
        parser.error(f"issue {args.issue} does not implement stage {args.stage!r}")
    fn(cfg, vintage=args.vintage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
