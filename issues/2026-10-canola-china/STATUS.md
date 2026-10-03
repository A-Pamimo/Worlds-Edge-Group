# Issue 1 build status

Branch: `weg-platform`. Full plan: research notes, decisions and risks are summarised below;
the method is in `METHODS.md`.

## Done (verified on synthetic data, CI green)

- Checkpoint 0: scaffold, manifest with SHA-256 enforcement, schemas, numbers.json writer, figure style, CI.
- Shared analysis methods with hand-computed tests.
- Downloaders and cleaners for StatCan CIMT, Trade Data Online, UN Comtrade, Bank of Canada, Grain Commission
  (tested against fixtures that mimic documented layouts; not yet run on live data).
- Issue 1 Q1-Q5, figures, report template and renderer, archive stage.

## Blocked until a session with network access and COMTRADE_API_KEY

The first session could not reach any data or primary-source host (proxy 403), so nothing below is done.

1. **Checkpoint 1, events.** Open every `source_url` in `events.yaml`. For each event, read date, effective date,
   rate and tariff lines from the primary page; set `status: CONFIRMED` and `verified_on`, or keep UNCONFIRMED with
   the reason. Find primary URLs for `ad_extension` and `pea_starch_ad`. Read the annex of 税委会公告2025年第3号
   (are 15149100/15149900 included?) and of 税委会公告2026年第2号 (exact lines suspended).
2. **Checkpoint 2, Canadian data.** `make download VINTAGE=latest` for boc, statcan_cimt, cgc, tdo.
   - Open one `CIMT-CICM_Dom_Exp_<year>.zip`: confirm member names, columns, whether a province column exists,
     units for the eight HS codes, how 2306.41 vs 2306.49 is populated. Adjust `weg/clean/statcan_cimt.py` Layout if needed.
   - Confirm TDO returns parseable HTML without JavaScript and how far back the monthly window goes. If not usable,
     inspect the CIMT web app REST backend for a province dimension.
   - Extend `concordance/countries.csv` for any UNMAPPED countries in `outputs/tables/clean_report.json`.
   - Report HS 9901 share per month as a diagnostic.
3. **Checkpoint 3, Comtrade.** getDa availability matrix for China and candidate markets; finalise `markets` in
   config from it; pull imports and exports.
4. **Checkpoint 4, reconciliation.** `make test` runs `tests/test_real_data.py` once data/clean exists; review
   `outputs/tables/reconciliation_china.csv` and tolerance bands.
5. Pin vintages in `config.yaml: data.vintages`, run `make analyze figures report`, commit outputs, then
   `make archive` and set `data.data_release`.

## Decisions taken with the user

- Shock window is the headline; relief window (from 2026-03) is a separate block; oil has no relief block.
- Province cost on a value basis; province tonnes are estimates and flagged.
- Raw snapshot per issue published as a GitHub release; `make download` resolves it unless VINTAGE=latest.
- Defaults applied: CAD headline currency, statsmodels trend model, slug `2026-10-canola-china`,
  data cut 2026-07 (bump to 2026-08 after the 2026-10-06 StatCan release), REPORT.md drafted by Claude.

## Research notes from the first session (all unconfirmed until checkpoint 1)

- Measures changed on 2026-03-01: meal and pea tariffs suspended to 2026-12-31; seed anti-dumping final duty 5.9%
  replaces the 75.8% deposit; the 100% oil tariff stays.
- Canada appears to export canola meal under 2306.41, not 2306.49.
- No public source appears to have province of origin and quantity in the same cell.
- Comtrade monthly import data is likely missing for UAE, Vietnam, Pakistan and Bangladesh.
- China customs (GACC) is browser-only behind a captcha; not usable in the pipeline.
