"""Paths, environment and issue configuration.

All paths derive from the repository root so `make all` behaves the same from any
working directory. Tests override roots by passing explicit paths to functions.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_CLEAN = ROOT / "data" / "clean"
MANIFEST_PATH = ROOT / "manifests" / "data_manifest.csv"
ISSUES_DIR = ROOT / "issues"
CONCORDANCE_DIR = Path(__file__).resolve().parent / "concordance"

GITHUB_REPO = "A-Pamimo/Worlds-Edge-Group"


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env into os.environ without overriding existing values."""
    path = path or (ROOT / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env(name: str, required: bool = False, default: str | None = None) -> str | None:
    load_dotenv()
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(
            f"Environment variable {name} is required. Copy .env.example to .env or export it."
        )
    return value


def issue_dir(slug: str, issues_dir: Path | None = None) -> Path:
    path = (issues_dir or ISSUES_DIR) / slug
    if not path.is_dir():
        raise FileNotFoundError(f"Issue directory not found: {path}")
    return path


def load_issue_config(slug: str, issues_dir: Path | None = None) -> dict[str, Any]:
    path = issue_dir(slug, issues_dir) / "config.yaml"
    with path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    cfg.setdefault("slug", slug)
    cfg["_dir"] = str(path.parent)
    return cfg


def load_events(slug: str, issues_dir: Path | None = None) -> list[dict[str, Any]]:
    path = issue_dir(slug, issues_dir) / "events.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return list(data.get("events", []))
