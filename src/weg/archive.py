"""Publish an issue's raw snapshot as GitHub release assets (decision D3).

`make archive ISSUE=<slug>` creates (or reuses) a release tagged `<slug>-data-<vintage-date>`
and uploads every manifest row for the issue, flattened with `download.base.asset_name`.
A token is needed only here (GITHUB_TOKEN), never stored. After upload, set
`data.data_release` in the issue config to the tag so `make download` resolves the archive.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

from weg import config
from weg.download.base import asset_name, http_get
from weg.manifest import Manifest

API = "https://api.github.com"


def _headers() -> dict[str, str]:
    token = config.env("GITHUB_TOKEN", required=True)
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def ensure_release(tag: str, repo: str = config.GITHUB_REPO, body: str = "") -> dict:
    url = f"{API}/repos/{repo}/releases/tags/{tag}"
    resp = requests.get(url, headers=_headers(), timeout=60)
    if resp.status_code == 200:
        return resp.json()
    resp = requests.post(f"{API}/repos/{repo}/releases", headers=_headers(), timeout=60,
                         json={"tag_name": tag, "name": tag, "body": body, "draft": False, "prerelease": False})
    resp.raise_for_status()
    return resp.json()


def upload_asset(release: dict, path: Path, name: str) -> dict:
    existing = {a["name"]: a for a in release.get("assets", [])}
    if name in existing:
        return existing[name]
    upload_url = release["upload_url"].split("{")[0]
    with path.open("rb") as fh:
        resp = requests.post(upload_url, params={"name": name}, data=fh, timeout=600,
                             headers={**_headers(), "Content-Type": "application/octet-stream"})
    resp.raise_for_status()
    return resp.json()


def archive_issue(cfg: dict, tag: str | None = None) -> str:
    manifest = Manifest(config.MANIFEST_PATH, root=config.ROOT)
    rows = [r for r in manifest.rows.values() if r.issue == cfg["slug"]]
    if not rows:
        raise RuntimeError("manifest has no rows for this issue; run make download first")
    problems = manifest.verify(cfg["slug"])
    if problems:
        raise RuntimeError("manifest does not match data/raw: " + "; ".join(problems[:5]))
    vintages = sorted({r.vintage for r in rows})
    tag = tag or f"{cfg['slug']}-data-{max(vintages)}"
    body = "Raw data snapshot for issue " + cfg["slug"] + "\n\nVintages: " + ", ".join(vintages) + "\n\n" + \
           "SHA-256 per file is recorded in manifests/data_manifest.csv at the commit that cut this release."
    release = ensure_release(tag, body=body)
    for r in sorted(rows, key=lambda r: r.raw_path):
        upload_asset(release, config.ROOT / r.raw_path, asset_name(r.raw_path))
    # also attach the manifest subset for convenience
    sub = config.ROOT / "manifests" / f"{cfg['slug']}.manifest.json"
    sub.write_text(json.dumps([r.__dict__ for r in sorted(rows, key=lambda r: r.raw_path)], indent=1) + "\n")
    upload_asset(release, sub, sub.name)
    print(f"[weg] archived {len(rows)} files to release {tag}; set data.data_release: {tag} in config.yaml")
    return tag
