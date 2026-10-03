import pytest

from weg.manifest import Manifest, ManifestMismatchError, sha256_of


def _setup(tmp_path):
    root = tmp_path
    raw = root / "data" / "raw" / "src" / "v1"
    raw.mkdir(parents=True)
    f = raw / "file.csv"
    f.write_text("a,b\n1,2\n")
    return root, f


def test_record_and_reload(tmp_path):
    root, f = _setup(tmp_path)
    m = Manifest(root / "manifests" / "data_manifest.csv", root=root)
    row = m.record(source="src", url_or_query="https://x/y", vintage="v1", raw_path=f, issue="t")
    assert row.sha256 == sha256_of(f)
    assert row.raw_path == "data/raw/src/v1/file.csv"
    m2 = Manifest(root / "manifests" / "data_manifest.csv", root=root)
    assert m2.lookup("src", "https://x/y", "v1") == row
    assert m2.verify() == []


def test_same_bytes_is_idempotent(tmp_path):
    root, f = _setup(tmp_path)
    m = Manifest(root / "manifests" / "data_manifest.csv", root=root)
    r1 = m.record(source="src", url_or_query="q", vintage="v1", raw_path=f, issue="t")
    r2 = m.record(source="src", url_or_query="q", vintage="v1", raw_path=f, issue="t")
    assert r1 == r2
    assert len(m.rows) == 1


def test_changed_bytes_same_vintage_raises(tmp_path):
    root, f = _setup(tmp_path)
    m = Manifest(root / "manifests" / "data_manifest.csv", root=root)
    m.record(source="src", url_or_query="q", vintage="v1", raw_path=f, issue="t")
    f.write_text("a,b\n1,3\n")
    with pytest.raises(ManifestMismatchError):
        m.record(source="src", url_or_query="q", vintage="v1", raw_path=f, issue="t")
    assert m.verify() == ["hash mismatch: data/raw/src/v1/file.csv"]


def test_new_vintage_is_a_new_row(tmp_path):
    root, f = _setup(tmp_path)
    m = Manifest(root / "manifests" / "data_manifest.csv", root=root)
    m.record(source="src", url_or_query="q", vintage="v1", raw_path=f, issue="t")
    f.write_text("a,b\n1,3\n")
    m.record(source="src", url_or_query="q", vintage="v2", raw_path=f, issue="t")
    assert len(m.rows) == 2


def test_csv_is_sorted_and_stable(tmp_path):
    root, f = _setup(tmp_path)
    p = root / "manifests" / "data_manifest.csv"
    m = Manifest(p, root=root)
    m.record(source="b", url_or_query="q", vintage="v1", raw_path=f, issue="t", downloaded_at_utc="2026-01-01T00:00:00Z")
    m.record(source="a", url_or_query="q", vintage="v1", raw_path=f, issue="t", downloaded_at_utc="2026-01-01T00:00:00Z")
    text = p.read_text()
    assert text.splitlines()[0] == "source,url_or_query,vintage,downloaded_at_utc,sha256,bytes,issue,raw_path"
    assert text.splitlines()[1].startswith("a,")
