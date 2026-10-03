# Methods — Issue 1: Canadian canola and peas after China's 2025 measures

Status: code complete on synthetic data; live-data sections (3.3, 5) are filled at checkpoints 2–4.
Every number cited in REPORT.md exists in `outputs/numbers.json` under the key given here.

## 1. Question

After China's 2025 tariffs on Canadian canola oil, meal and peas, and its anti-dumping measures on
Canadian canola seed: where did Canadian exports go, at what price, and what did it cost Canada?

Products (HS 6): 1205.10 canola seed; 1514.11/19/91/99 canola oil; 2306.41 and 2306.49 oilseed cake
and meal (2306.41 is the low-erucic line under which canola meal is classified since HS 2022; 2306.49 is
reported as a residual); 0713.10 dried peas.

## 2. Events and windows

Every event lives in `events.yaml` with a primary `source_url`, a `status` and a `verified_on` date.
Nothing with status UNCONFIRMED is cited in the report; `config.yaml: publication_ready` cannot be true
while any event referenced by a product is unconfirmed (`tests/test_events.py`).

Three regimes, not two. The tariff of 20 March 2025 (oil, meal, peas) and the anti-dumping deposit of
14 August 2025 (seed) were followed on 1 March 2026 by a suspension of the meal and pea tariffs and a
cut of the seed duty; the oil tariff stayed. Windows per product (`config.yaml: windows`):

| Product | Event month | Pre (12 months) | Shock | Relief |
|---|---|---|---|---|
| Canola seed | 2025-08 | 2024-08 to 2025-07 | 2025-09 to 2026-02 | 2026-03 to latest |
| Canola oil | 2025-03 | 2024-03 to 2025-02 | 2025-04 to 2026-02 | none |
| Canola meal | 2025-03 | 2024-03 to 2025-02 | 2025-04 to 2026-02 | 2026-03 to latest |
| Dried peas | 2025-03 | 2024-03 to 2025-02 | 2025-04 to 2026-02 | 2026-03 to latest |

The event month itself is a partial month and belongs to neither window. Headline numbers use the shock
window; the relief block (section 4.6) asks whether volumes and prices returned.

## 3. Data

### 3.1 Sources

| Table | Source | Access | Unit |
|---|---|---|---|
| `ca_exports` | Statistics Canada, Canadian International Merchandise Trade bulk files (71-607-X2021004), domestic exports by HS 8, country, month | public zip per year, no key | CAD, kg |
| `ca_exports_province` | Government of Canada Trade Data Online, domestic exports by HS 6, country, province of origin, month | public report pages, no key | CAD only |
| `comtrade_imports` | UN Comtrade, monthly HS, imports of China and each candidate market from all partners; exports of candidate markets and competitors | API, free key | USD, kg |
| `fx_monthly` | Bank of Canada Valet, monthly average rates | API, no key | CAD per USD |
| Cross-check | Canadian Grain Commission monthly exports by destination | public CSV | tonnes |

Every raw file is recorded in `manifests/data_manifest.csv` with its URL or query, vintage, download
time and SHA-256. Re-downloading the same vintage with different bytes fails. Finished issues publish
their raw snapshot as a GitHub release so `make all` reproduces the numbers after sources revise.

### 3.2 Conventions

- Quantities in tonnes (kg / 1000). Canadian quantities must be in kilograms (KGM); the pipeline fails
  on any other unit for these codes.
- Values: CAD from Canadian data. Comtrade values (USD, CIF for imports) are converted at the Bank of
  Canada monthly average for the same calendar month when a CAD figure is needed.
- Unit value = value / tonnes, undefined where tonnes are zero.
- Domestic exports only. Province means province of origin in the StatCan sense (where the goods were
  grown, extracted or manufactured).

### 3.3 Known limits (completed with live data)

- Confidential cells are moved by Statistics Canada to HS 9901 rather than flagged. Share of 9901 by
  month is reported as a diagnostic; concentrated lines (oil, meal) and province cells are most exposed.
- Revisions: current year revised each release; prior year with the January and February references and
  quarterly; two prior years in the February release.
- Partner coverage: markets without monthly import data in Comtrade are analysed from Canadian data only
  and listed under `q1.<product>.transshipment.no_partner_data`.

## 4. Methods

### 4.1 Seasonality and the trend model

For each product and destination series y_t (tonnes, or CAD/t for prices) the model

    log y_t = a + b·t + Σ_{k=2..12} m_k·1[month_t = k] + e_t

is fit by ordinary least squares on January 2019 to December 2024 (`counterfactuals.B`). Zero months
cannot enter a log fit and are dropped; a series with fewer than 24 positive months, or without all
twelve calendar months, uses the product-level (all-destination) factors instead. Month factors are
exp(m_k) normalised to geometric mean 1. Seasonal adjustment divides by the factor of the month.
Code: `src/weg/analysis/seasonality.py`.

### 4.2 Counterfactuals

- A, same months of the prior year: value twelve months earlier. No model. Confounded by crop size.
- B, trend and seasonal: the model above projected into the window.
- B′, sensitivity: B with January 2020 to December 2021 excluded from the fit.

All three are computed for every number; B is the headline (`meta.headline_counterfactual`).
A series that cannot be fit under B falls back to A for that series.
Code: `src/weg/analysis/counterfactual.py`.

### 4.3 Q1 Diversion

For each post month t: loss_t = max(CF_China,t − actual_China,t, 0); gain_d,t = actual_d,t − CF_d,t for
every other destination d (signed); positive_t = Σ_d max(gain_d,t, 0); matched_t = min(loss_t, positive_t);
never_resold_t = loss_t − matched_t.

- `q1.<p>.<cf>.<w>.loss_t`: Σ loss_t.
- `q1.<p>.<cf>.<w>.reappeared_share`: Σ matched_t / Σ loss_t (monthly matching, headline).
- `q1.<p>.<cf>.<w>.reappeared_share_period`: min(1, Σ positive_t / Σ loss_t) (period matching).
- `q1.<p>.<cf>.<w>.top_destinations` and shares of positive gain: where the volume went.
- `q1.<p>.<cf>.<w>.world_change_pct`: all-destination actual vs counterfactual, so the reader sees
  whether total exports fell or merely moved.

Transshipment screen (`q1.<p>.transshipment.*`): for the top gainers, the gain in Canadian data is
compared with the gainer's own reported imports from Canada and with the gainer's exports of the same
product to China (both from Comtrade). A gain not matched by the partner's imports, or matched by a rise
in the partner's exports to China, is flagged and reported separately; it is never netted out.
Code: `src/weg/analysis/diversion.py`, `issues/.../analysis/q1_diversion.py`.

### 4.4 Q2 Price

Unit values in CAD/t per destination, seasonally adjusted with the destination's own factors (fallback:
product-level). For China and the five largest shock-window destinations:

- `q2.<p>.<d>.<w>.pct_change_sa`: post-window mean over pre-window mean minus one, same destination.
- `q2.<p>.<d>.<w>.pct_change_relative`: the same change in the ratio of the destination's unit value to
  the all-destinations-ex-China unit value, which nets out world price moves. This is the headline
  measure of a destination-specific discount.
- Destinations with fewer than three pre-window months (`price.min_pre_months`) report NaN.
- `q2.<p>.new_buyers.*`: volume-weighted across destinations with positive gains under B.

### 4.5 Q3 Replacement

China-reported imports (Comtrade reporter CHN, flow M) by origin per product. Shares pre vs shock, change
in China's total monthly imports, top gainers by share change. The shock window is clipped to the months
China has published (`q3.<p>.coverage_last_period`).

### 4.6 Q4 Cost

- Never-resold revenue = Σ_t never_resold_t × CF unit value China,t, where the China price
  counterfactual uses the same specification as the volume counterfactual (A: prior-year price; B, B′:
  trend+seasonal fit on the price series), with the ex-China benchmark as fallback.
- Discount = Σ_d Σ_t alloc_d,t × (CF unit value_d,t − actual unit value_d,t), where alloc_d,t allocates
  matched_t across destinations in proportion to their positive gains. Signed: a premium reduces cost.
- Cost = never-resold revenue + discount, under A, B and B′ (`q4.<p>.<cf>.shock.cost_cad`;
  `q4.total.<cf>.shock.cost_cad` sums products).
- Sensitivity `cost_cad_period_matching`: never-resold volume from window totals instead of monthly matching.
- Caveat: volume not exported in the window may be stocked and sold later; "cost to date" is not a
  permanent loss. The relief block shows whether volume returned.

### 4.7 Q5 Strategic cuts

- Province: the Q1 accounting is run on province × destination value series (Trade Data Online), giving
  `lost_revenue_cad`, `reappeared_value_cad` and `net_cost_cad` per province under each counterfactual.
  Tonnes at province level are estimates: provincial value divided by the national unit value for the same
  product, destination and month, flagged `estimated: true`.
- New buyers vs China (`q5.<p>.gap.*`): monthly gap = new-buyer SA unit value − China's pre-window SA
  mean; OLS slope of |gap| on time; narrowing if t < −2, widening if t > 2, else stable.
- Concentration (`q5.<p>.concentration.<w>.*`): HHI (0–1) and top-3 share of non-China destinations by tonnes.
- Relief (`q5.relief.<p>.*`): China volume in the relief window relative to counterfactual B and to the
  shock-window monthly mean.

### 4.8 Reconciliation (test)

Canada-reported exports to China vs China-reported imports from Canada at lags 0–2 months; the best lag
minimises the mean absolute log of the 3-month rolling ratio; annual ratios of complete years must fall
within the per-product band in `config.yaml: reconciliation.tolerance` (CIF > FOB and transit time are
expected, so bands are asymmetric). Output: `outputs/tables/reconciliation_china.csv`.

## 5. Known limits (completed with live data)

To be completed at checkpoints 2–4: suppression diagnostics, partner coverage matrix, unmapped countries.
