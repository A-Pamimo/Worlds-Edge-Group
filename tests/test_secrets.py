"""No secrets in tracked files."""
import re
import subprocess

from weg import config

PATTERNS = [
    re.compile(r"COMTRADE_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9]{16,}"),
    re.compile(r"Ocp-Apim-Subscription-Key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}"),
    re.compile(r"subscription-key=[A-Za-z0-9]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
]


def tracked_files():
    out = subprocess.check_output(["git", "ls-files"], cwd=config.ROOT, text=True)
    return [config.ROOT / line for line in out.splitlines() if line]


def test_no_env_file_tracked():
    names = {p.name for p in tracked_files()}
    assert ".env" not in names


def test_no_key_like_strings_in_tracked_text():
    for path in tracked_files():
        if path.suffix in {".png", ".jpg", ".parquet", ".zip", ".svg"} or not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pat in PATTERNS:
            assert not pat.search(text), f"secret-like string in {path.relative_to(config.ROOT)}"
