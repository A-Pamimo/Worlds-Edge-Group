# Where Canadian canola and peas went after China's 2025 measures

*World's Edge Group — Canada–Asia Trade, Issue 1. Draft structure; prose is written once live numbers exist.
Every figure in this document is a placeholder resolved from `outputs/numbers.json` by `make report`.*

Data through {{meta.latest_period}}. Headline counterfactual: {{meta.headline_counterfactual}} (all three reported in the appendix).

## The question

After China's 2025 tariffs on Canadian canola oil, meal and peas, and its anti-dumping measure on canola seed:
where did the exports go, at what price, and what did it cost Canada?

## 1. Diversion: what left China and what reappeared elsewhere

| Product | Lost to China (shock window) | Reappeared elsewhere | Never resold | Top destinations |
|---|---|---|---|---|
| Canola seed | {{q1.canola_seed.B.shock.loss_t|kt}} | {{q1.canola_seed.B.shock.reappeared_share|pct}} | {{q1.canola_seed.B.shock.never_resold_t|kt}} | {{q1.canola_seed.B.shock.top_destinations|list}} |
| Canola oil | {{q1.canola_oil.B.shock.loss_t|kt}} | {{q1.canola_oil.B.shock.reappeared_share|pct}} | {{q1.canola_oil.B.shock.never_resold_t|kt}} | {{q1.canola_oil.B.shock.top_destinations|list}} |
| Canola meal | {{q1.canola_meal.B.shock.loss_t|kt}} | {{q1.canola_meal.B.shock.reappeared_share|pct}} | {{q1.canola_meal.B.shock.never_resold_t|kt}} | {{q1.canola_meal.B.shock.top_destinations|list}} |
| Dried peas | {{q1.dried_peas.B.shock.loss_t|kt}} | {{q1.dried_peas.B.shock.reappeared_share|pct}} | {{q1.dried_peas.B.shock.never_resold_t|kt}} | {{q1.dried_peas.B.shock.top_destinations|list}} |

Total exports of each product versus counterfactual, all destinations: seed {{q1.canola_seed.B.shock.world_change_pct|signed_pct}},
oil {{q1.canola_oil.B.shock.world_change_pct|signed_pct}}, meal {{q1.canola_meal.B.shock.world_change_pct|signed_pct}},
peas {{q1.dried_peas.B.shock.world_change_pct|signed_pct}}.

Transshipment screen: destinations whose own trade data does not match the Canadian gain, or whose exports to China rose —
seed: {{q1.canola_seed.transshipment.flagged|list}}; meal: {{q1.canola_meal.transshipment.flagged|list}}.

![Loss and reappearance](outputs/figures/q1_loss_reappearance.svg)

## 2. Price: did the new buyers pay less?

New buyers, volume-weighted, seasonally adjusted, against the same markets' pre-event prices:
seed {{q2.canola_seed.new_buyers.shock.pct_change_sa|signed_pct}} (relative to the ex-China benchmark {{q2.canola_seed.new_buyers.shock.pct_change_relative|signed_pct}}),
oil {{q2.canola_oil.new_buyers.shock.pct_change_sa|signed_pct}} ({{q2.canola_oil.new_buyers.shock.pct_change_relative|signed_pct}}),
meal {{q2.canola_meal.new_buyers.shock.pct_change_sa|signed_pct}} ({{q2.canola_meal.new_buyers.shock.pct_change_relative|signed_pct}}),
peas {{q2.dried_peas.new_buyers.shock.pct_change_sa|signed_pct}} ({{q2.dried_peas.new_buyers.shock.pct_change_relative|signed_pct}}).

![Unit values, canola seed](outputs/figures/q2_unit_values_canola_seed.svg)

## 3. Replacement: who supplied China instead

Canada's share of China's imports, pre versus shock: seed {{q3.canola_seed.pre.canada_share|pct}} → {{q3.canola_seed.shock.canada_share|pct}}
(gainers: {{q3.canola_seed.shock.top_gainers|list}}); meal {{q3.canola_meal.pre.canada_share|pct}} → {{q3.canola_meal.shock.canada_share|pct}}
(gainers: {{q3.canola_meal.shock.top_gainers|list}}); peas {{q3.dried_peas.pre.canada_share|pct}} → {{q3.dried_peas.shock.canada_share|pct}}
(gainers: {{q3.dried_peas.shock.top_gainers|list}}). China's own data runs to {{q3.canola_seed.coverage_last_period}}.

## 4. Cost to Canada

Shock window, counterfactual B: {{q4.total.B.shock.cost_cad|cad_m}}, of which revenue on volume never resold
{{q4.total.B.shock.never_resold_revenue_cad|cad_m}} and the discount on volume that was {{q4.total.B.shock.discount_cad|cad_m}}.
Under counterfactual A: {{q4.total.A.shock.cost_cad|cad_m}}. Excluding 2020–2021 from the trend (B′): {{q4.total.B_prime.shock.cost_cad|cad_m}}.

![Cost by counterfactual](outputs/figures/q4_cost_by_counterfactual.svg)

## 5. Who bears it

**By province** (value basis, net of value that reappeared elsewhere from the same province): see
`q5.province.total.B.shock.net_cost_by_province_cad` and the figure below.

![Province](outputs/figures/q5_province_cost.svg)

**New buyers versus China's old price**: canola seed gap {{q5.canola_seed.gap.mean_gap_pct|signed_pct}}, trend {{q5.canola_seed.gap.classification}};
canola meal gap {{q5.canola_meal.gap.mean_gap_pct|signed_pct}}, trend {{q5.canola_meal.gap.classification}}.

**Concentration of the new destinations** (HHI of non-China destinations, pre → shock): seed
{{q5.canola_seed.concentration.pre.hhi_ex_china|ratio}} → {{q5.canola_seed.concentration.shock.hhi_ex_china|ratio}};
meal {{q5.canola_meal.concentration.pre.hhi_ex_china|ratio}} → {{q5.canola_meal.concentration.shock.hhi_ex_china|ratio}}.

**After 1 March 2026**: China volume relative to counterfactual in the relief window — meal {{q5.relief.canola_meal.china_volume_ratio_to_cf|ratio}},
peas {{q5.relief.dried_peas.china_volume_ratio_to_cf|ratio}}, seed {{q5.relief.canola_seed.china_volume_ratio_to_cf|ratio}}.

**The most surprising result.** *(written after live numbers; must cite keys above)*

**The question the data cannot answer.** *(written after live numbers)*

## The decision this forces

*(written after live numbers; one paragraph, neutral, naming who decides and by when)*

## Appendix: every counterfactual

See `outputs/tables/q4_cost.csv` and `outputs/numbers.json`. Methods: `METHODS.md`.
