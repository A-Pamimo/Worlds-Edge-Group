"""HTTP fetch with retries, archive-first resolution and manifest recording.

Resolution order for a raw file (decision D3):
  1. If the issue config pins `data_release` and vintage != "latest", try the GitHub
     release asset for that file. Its SHA-256 must match the manifest.
  2. Otherwise fetch from the live source URL.
Either way the bytes land in data/raw/<source>/<vintage>/<name> and the manifest
records (source, url_or_query, vintage, sha256). A second download of the same
vintage with different bytes raises ManifestMismatchError.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

from weg import config
from weg.manifest import Manifest

USER_AGENT = "weg-trade-reports/0.1 (+https://github.com/A-Pamimo/Worlds-Edge-Group)"
RETRY_STATUS = {429, 500, 502, 503, 504}


def asset_name(raw_rel_path: str) -> str:
    """Release assets cannot contain '/', so flatten the relative raw path."""
    return raw_rel_path.replace("/", "__")


def archive_url(raw_rel_path: str, release_tag: str, repo: str = config.GITHUB_REPO) -> str:
    return f"https://github.com/{repo}/releases/download/{release_tag}/{asset_name(raw_rel_path)}"


def http_get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 120,
    retries: int = 4,
    backoff: float = 2.0,
    session: requests.Session | None = None,
) -> requests.Response:
    sess = session or requests.Session()
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = sess.get(url, params=params, headers=hdrs, timeout=timeout)
            if resp.status_code in RETRY_STATUS and attempt < retries:
                wait = float(resp.headers.get("Retry-After", backoff * (2**attempt)))
                time.sleep(min(wait, 120))
                continue
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (2**attempt))
                continue
            raise
    raise RuntimeError(f"unreachable: {url}") from last_exc


def fetch(
    url: str,
    *,
    source: str,
    vintage: str,
    name: str,
    issue: str,
    query: str | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    release_tag: str | None = None,
    raw_root: Path | None = None,
    manifest: Manifest | None = None,
    force: bool = False,
) -> Path:
    """Download one raw file, record it in the manifest, return its path.

    `query` is what the manifest records as url_or_query (defaults to the URL with
    params). Secrets must never be part of `query` or `url`; pass keys via headers.
    """
    raw_root = raw_root or config.DATA_RAW
    manifest = manifest or Manifest(config.MANIFEST_PATH, root=config.ROOT)
    dest = raw_root / source / vintage / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    rel = dest.resolve().relative_to(manifest.root.resolve()).as_posix()
    record_query = query or _with_params(url, params)

    existing = manifest.lookup(source, record_query, vintage)
    if dest.exists() and existing is not None and not force:
        # already present: verify bytes against the manifest, fail loudly otherwise
        manifest.record(source=source, url_or_query=record_query, vintage=vintage, raw_path=dest, issue=issue)
        return dest

    fetched = False
    if release_tag and vintage != "latest" and existing is not None:
        try:
            resp = http_get(archive_url(rel, release_tag), retries=2)
            dest.write_bytes(resp.content)
            fetched = True
        except requests.HTTPError:
            fetched = False
    if not fetched:
        resp = http_get(url, params=params, headers=headers)
        dest.write_bytes(resp.content)
    manifest.record(source=source, url_or_query=record_query, vintage=vintage, raw_path=dest, issue=issue)
    return dest


def _with_params(url: str, params: dict[str, Any] | None) -> str:
    if not params:
        return url
    q = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{url}?{q}"
