"""`python -m weg <stage> --issue <slug>`: dispatch to issues/<slug>/analysis/run.py."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from weg import config

STAGES = ("download", "clean", "analyze", "figures", "report", "archive")


def load_issue_runner(slug: str, issues_dir: Path | None = None) -> ModuleType:
    """Import issues/<slug>/analysis as a package (so its modules can import each other) and return run."""
    pkg_dir = config.issue_dir(slug, issues_dir) / "analysis"
    pkg_name = f"issue_{slug.replace('-', '_')}"
    if pkg_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(pkg_name, pkg_dir / "__init__.py", submodule_search_locations=[str(pkg_dir)])
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {pkg_dir}")
        pkg = importlib.util.module_from_spec(spec)
        sys.modules[pkg_name] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(f"{pkg_name}.run")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="weg")
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--vintage", default="pinned", help="'pinned' (default) or 'latest'")
    args = parser.parse_args(argv)
    cfg = config.load_issue_config(args.issue)
    runner = load_issue_runner(args.issue)
    if args.stage == "report":
        from weg.report import render_issue

        print(render_issue(Path(cfg["_dir"])))
        return 0
    fn = getattr(runner, args.stage, None)
    if fn is None:
        parser.error(f"issue {args.issue} does not implement stage {args.stage!r}")
    fn(cfg, vintage=args.vintage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
