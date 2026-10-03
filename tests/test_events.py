"""Events are the only hand-entered facts in the repo; they must be complete and, before
publication, confirmed against primary sources."""
from datetime import date

import pytest

from weg import config

ISSUES = sorted(p.name for p in config.ISSUES_DIR.iterdir() if (p / "config.yaml").exists())
REQUIRED = {"id", "date", "actor", "instrument", "measure", "source_url", "status", "reason", "verified_on"}


@pytest.mark.parametrize("slug", ISSUES)
def test_events_complete(slug):
    events = config.load_events(slug)
    assert events, "events.yaml has no events"
    ids = [e["id"] for e in events]
    assert len(ids) == len(set(ids)), "duplicate event ids"
    for e in events:
        missing = REQUIRED - set(e)
        assert not missing, f"{e.get('id')}: missing {missing}"
        date.fromisoformat(e["date"])
        if e.get("effective"):
            date.fromisoformat(e["effective"])
        assert e["status"] in {"CONFIRMED", "UNCONFIRMED"}
        if e["status"] == "CONFIRMED":
            assert e["source_url"], f"{e['id']}: CONFIRMED needs a source_url"
            assert e["verified_on"], f"{e['id']}: CONFIRMED needs verified_on"
        else:
            assert e["reason"], f"{e['id']}: UNCONFIRMED needs a reason"


@pytest.mark.parametrize("slug", ISSUES)
def test_config_events_exist_and_gate(slug):
    cfg = config.load_issue_config(slug)
    events = {e["id"]: e for e in config.load_events(slug)}
    referenced = {eid for prod in cfg["products"].values() for eid in prod.get("events", [])}
    unknown = referenced - set(events)
    assert not unknown, f"config references unknown events {unknown}"
    if cfg.get("publication_ready"):
        unconfirmed = [eid for eid in referenced if events[eid]["status"] != "CONFIRMED"]
        assert not unconfirmed, f"publication_ready but unconfirmed events: {unconfirmed}"


@pytest.mark.parametrize("slug", ISSUES)
def test_windows_consistent(slug):
    cfg = config.load_issue_config(slug)
    for product, w in cfg["windows"].items():
        assert product in cfg["products"]
        pre0, pre1 = w["pre"]
        s0, s1 = w["shock"]
        assert pre0 < pre1 < w["event_month"] <= s0 < s1, product
        if w.get("relief"):
            r0, r1 = w["relief"]
            assert s1 < r0 <= r1 <= cfg["data"]["latest_period"], product
