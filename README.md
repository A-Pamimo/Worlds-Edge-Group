# World's Edge Group — Canada–Asia trade reports

This repository holds two things:

1. The static website (`index.html` and friends) — unchanged by the research platform.
2. A reproducible research platform for the monthly Canada–Asia trade report series.
   Shared code lives in `src/weg/`; each issue lives in `issues/YYYY-MM-slug/`.

Every number and chart in a report is produced by code from public data. `make all` on a clean
clone reproduces an issue's `outputs/numbers.json` exactly.

## Quick start

```bash
cp .env.example .env            # add COMTRADE_API_KEY (free key from comtradedeveloper.un.org)
make setup                      # Python 3.12 via uv, frozen lock file
make test                       # unit tests on synthetic fixtures, no network
make all ISSUE=2026-10-canola-china
```

Targets: `setup`, `download`, `clean`, `analyze`, `figures`, `all`, `test`, `archive`, `lock`.
`make download VINTAGE=latest` pulls live sources and records a new data vintage; the default
resolves the vintage pinned in the issue's `config.yaml` (from the issue's GitHub release once
published).

## Layout

| Path | What |
|---|---|
| `src/weg/download/` | fetchers (StatCan CIMT, Trade Data Online, UN Comtrade, Bank of Canada, Canadian Grain Commission) |
| `src/weg/clean/` | raw files → standard parquet tables in `data/clean/` (schemas in `src/weg/schemas.py`) |
| `src/weg/analysis/` | shared methods: seasonality, counterfactuals, unit values, diversion, concentration, reconciliation |
| `src/weg/concordance/` | country, province, HS6 and unit lookups |
| `src/weg/figures.py` | chart style (primary `#1B2A41`, no titles) and deterministic SVG+PNG export |
| `src/weg/numbers.py` | `numbers.json` writer (sorted keys, fixed rounding, no timestamps) |
| `manifests/data_manifest.csv` | every raw file: source, URL or query, vintage, download time, SHA-256 |
| `issues/<slug>/` | `config.yaml`, `events.yaml`, `analysis/`, `METHODS.md`, `outputs/` |
| `tests/` | schema and duplicate checks, manifest checksum enforcement, events gate, reproducibility |

`data/raw/` and `data/clean/` are gitignored. Re-downloading the same vintage with different
bytes fails loudly (`ManifestMismatchError`).

## Rules

- Nothing hand-typed: headline numbers come from `outputs/numbers.json`, charts from `make figures`.
- Events (dates, rates, tariff lines) come only from primary sources listed in `events.yaml`,
  each with a `status`. An issue cannot be marked `publication_ready` while a referenced event is
  `UNCONFIRMED`.
- Analysis is neutral: windows, thresholds and counterfactual choices are pre-registered in
  `config.yaml`, and every result is reported under every pre-registered counterfactual.
- No secrets in the repo. Keys come from environment variables.
