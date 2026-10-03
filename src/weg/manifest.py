"""Data manifest: one row per raw file, with SHA-256, vintage and provenance.

Rule from the brief: re-downloading the same (source, query, vintage) must fail loudly
if the bytes differ. `Manifest.record` enforces that. The CSV is written in a fixed
column order and sorted, so diffs stay reviewable.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = [
    "source",
    "url_or_query",
    "vintage",
    "downloaded_at_utc",
    "sha256",
    "bytes",
    "issue",
    "raw_path",
]


class ManifestMismatchError(RuntimeError):
    """Same source/query/vintage, different bytes."""


@dataclass(frozen=True)
class ManifestRow:
    source: str
    url_or_query: str
    vintage: str
    downloaded_at_utc: str
    sha256: str
    bytes: int
    issue: str
    raw_path: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source, self.url_or_query, self.vintage)


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


class Manifest:
    def __init__(self, path: Path, root: Path | None = None):
        self.path = Path(path)
        # raw_path is stored relative to root so the manifest is portable
        self.root = Path(root) if root else self.path.parent.parent
        self.rows: dict[tuple[str, str, str], ManifestRow] = {}
        if self.path.exists():
            with self.path.open(newline="", encoding="utf-8") as fh:
                for rec in csv.DictReader(fh):
                    row = ManifestRow(
                        source=rec["source"],
                        url_or_query=rec["url_or_query"],
                        vintage=rec["vintage"],
                        downloaded_at_utc=rec["downloaded_at_utc"],
                        sha256=rec["sha256"],
                        bytes=int(rec["bytes"]),
                        issue=rec["issue"],
                        raw_path=rec["raw_path"],
                    )
                    self.rows[row.key] = row

    def lookup(self, source: str, url_or_query: str, vintage: str) -> ManifestRow | None:
        return self.rows.get((source, url_or_query, vintage))

    def record(
        self,
        *,
        source: str,
        url_or_query: str,
        vintage: str,
        raw_path: Path,
        issue: str,
        downloaded_at_utc: str | None = None,
    ) -> ManifestRow:
        raw_path = Path(raw_path)
        digest = sha256_of(raw_path)
        rel = raw_path.resolve().relative_to(self.root.resolve()).as_posix()
        existing = self.lookup(source, url_or_query, vintage)
        if existing is not None:
            if existing.sha256 != digest:
                raise ManifestMismatchError(
                    f"Checksum mismatch for source={source!r} vintage={vintage!r} "
                    f"query={url_or_query!r}: manifest has {existing.sha256[:12]}..., "
                    f"download has {digest[:12]}.... The source changed under the same "
                    f"vintage. Bump the vintage explicitly or restore the archived file."
                )
            return existing
        row = ManifestRow(
            source=source,
            url_or_query=url_or_query,
            vintage=vintage,
            downloaded_at_utc=downloaded_at_utc
            or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            sha256=digest,
            bytes=raw_path.stat().st_size,
            issue=issue,
            raw_path=rel,
        )
        self.rows[row.key] = row
        self.write()
        return row

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for row in sorted(self.rows.values(), key=lambda r: (r.source, r.vintage, r.url_or_query)):
                writer.writerow(asdict(row))

    def verify(self, issue: str | None = None) -> list[str]:
        """Return a list of problems (missing raw files, hash mismatches)."""
        problems: list[str] = []
        for row in self.rows.values():
            if issue and row.issue != issue:
                continue
            path = self.root / row.raw_path
            if not path.exists():
                problems.append(f"missing: {row.raw_path}")
            elif sha256_of(path) != row.sha256:
                problems.append(f"hash mismatch: {row.raw_path}")
        return problems
