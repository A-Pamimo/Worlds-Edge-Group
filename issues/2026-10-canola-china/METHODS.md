# Methods — Issue 1: Canadian canola and peas after China's 2025 measures

Status: scaffold (checkpoint 0). Sections are completed as each checkpoint lands.

## 1. Question

After China's 2025 tariffs on Canadian canola oil, meal and peas, and its anti-dumping measures on
Canadian canola seed: where did Canadian exports go, at what price, and what did it cost Canada?

## 2. Events and windows

See `events.yaml`. Every event carries a `status`; nothing with status UNCONFIRMED may be cited in the
report, and `config.yaml: publication_ready` cannot be set to true while any referenced event is
unconfirmed (enforced by `tests/test_events.py`).

Windows (config `windows`): `pre` is the 12 months ending the month before the event month; `shock` runs
from the first full month in force to February 2026; `relief` runs from March 2026 to the latest
available month for products whose measure was suspended or reduced on 1 March 2026.

## 3. Data

To be completed at checkpoints 2–3 (sources, vintages, suppression, revisions, reconciliation).

## 4. Methods

To be completed at checkpoints 5–9 (seasonality, counterfactuals, diversion, price, replacement, cost, cuts).

## 5. Known limits

To be completed.
