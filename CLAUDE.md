# Working rules for this repository

- Research platform: Python 3.12, `uv` with committed `uv.lock`. Run `make test` before every commit.
- Shared, issue-agnostic code goes in `src/weg/`. Issue-specific code goes in `issues/<slug>/analysis/`.
- Every number in a report must be written by `weg.numbers.NumbersWriter` into `outputs/numbers.json`.
  Never type a number into METHODS.md or REPORT.md that is not in numbers.json.
- Every chart is produced by `make figures` through `weg.figures` (SVG + PNG, primary #1B2A41, no titles).
- Event dates, rates and tariff lines come only from `issues/<slug>/events.yaml` with a primary
  `source_url`. Never add an event from memory; mark it UNCONFIRMED with a reason if the page was not opened.
- Analysis is neutral. Do not choose windows, thresholds or counterfactuals to favour a story; they are
  pre-registered in `config.yaml` and every pre-registered variant is reported.
- `data/raw/` and `data/clean/` are gitignored. Every raw file is recorded in `manifests/data_manifest.csv`
  with SHA-256. Same vintage + different bytes must raise, never silently overwrite.
- Secrets only via environment variables (`.env` is gitignored; `.env.example` lists the names).
- The static website files at the repo root are not part of the platform; leave them alone.
