# Frozen IDA1 evaluation plan, version 1

Frozen 21 October 2026 before acquiring usable historical IDA1 data. The 2025 DA results have already been inspected: this is a retrospective matched comparison, not a fresh unseen performance claim. Machine-readable settings: `config/intraday_evaluation_v1.json`. Amendments require a new version, rationale and explicit disclosure of whether outcomes were already inspected.

## Primary comparison and boundaries

Use the existing continuous seven-day DA base case for DE-LU, 9 January through 30 September 2025. Keep its trades, prices and fees unchanged. Allocate hourly MWh and fees across four quarter-hours; hold original MW constant and interpolate SOC consistently. Each daily ID adjustment must preserve original opening AND closing SOC. This deliberately isolates intraday value and does not allow ID optimisation to alter subsequent DA commitments. Report the boundary restriction as a limitation.

Primary experiment: prior-local-day same-quarter IDA1 price forecast, one D-1 14:30 local decision, with only publication-confirmed available prices. Average repeated local source quarters during autumn DST; if a source quarter does not exist or is unavailable, retain DA for the entire target day. No training or tuning is necessary for this primary baseline. Optional learned spread forecasts require a separately versioned training/validation plan.

A market-data timestamp alone does not prove publication availability. A supplier publication timestamp or documented results-availability evidence is required. The published nominal results schedule cannot prove no delays occurred on each historical day. Unknown availability blocks that predictor; do not assume instant availability.

## Fixed simulation assumptions

Battery 1 MW / 2 MWh, 90% round-trip efficiency, EUR10 per MWh physically discharged. ID fee EUR1 per absolute MWh traded (illustrative, not an EPEX quote). Base cap 2 MW equivalent per direction = 0.5 MWh per quarter-hour, enough to reverse a full-power 1 MW position; battery power itself remains 1 MW. Fees and caps apply to incremental trades, not net physical throughput.

Full-fill, price-taking clearing-price settlement and continuous quantities are explicitly idealised. Exchange volume tick, bid price limits, coupled order acceptance and partial fills are not implemented. A 0.1 MW tick is 0.025 MWh in 15 minutes; post-hoc rounding can break SOC feasibility and is prohibited. Do not imply the continuous relaxation is an exchange-compliant order strategy. Joint acceptance is not demonstrated by aggregate auction turnover.

Run each fee in [0, 0.5, 1, 2] EUR/MWh with cap 2 MW, and each cap in [0, 0.5, 1, 2] MW with fee 1. Re-optimise for each case; do not merely subtract fees from the base schedule. These sensitivities are fixed before outcomes, not used to cherry-pick a winning model. No-adjustment control must have zero incremental margin. Perfect-ID foresight, if added, is an explicitly labelled upper bound on the same intervals and constraints.

## Missing data and exception handling

Every expected local day is recorded. Structural errors (duplicate instants, wrong product, naive times, misaligned intervals, cleared missing prices) fail validation. Missing/cancelled/decoupled/unknown auction intervals make the whole day ineligible for adjustment; do not fill prices. The strategy retains original DA for that day. An eligible-day comparison and a full-window no-adjustment-fallback comparison must both disclose coverage and reasons. Never use a missing settlement as zero EUR/MWh. Solver or physical-check failure blocks reporting, rather than silently dropping a loss day.

## Metrics and diagnostics

Primary metric: combined net margin minus unchanged DA-only net margin. Report signed sales cashflow and purchase expenditure, absolute buy/sell MWh, ID fees, revised and original cycling cost, change in discharged MWh, losing-adjustment days (daily delta < -EUR0.000001), worst daily delta, and maximum physical residual. Negative-price sales can be negative revenue; negative-price purchases can be negative expenditure. Keep those signs.

The canonical metrics helper validates matched intervals, DA cashflows, net margins, SOC and physical balance. Historical aggregation must include original DA cashflows on fallback days and zero incremental trades. For five worst and three best local days (ties by date), show actual and forecast ID prices, DA prices, original/revised dispatch and SOC, with an accounting explanation. Avoid treating hindsight-selected case studies as forecast features.

## Ready-to-run gates

Schema and DST utilities are tested using synthetic data. A provider adapter, publication evidence, permitted-use record and historical coverage must still be validated on delivery. Supplier CSVs may need delimiter, decimal and timezone mapping. Do not use the 2020 legacy sample or 2026 single day as the 2025 history. Before adding later untouched tests, lock dates from coverage alone before reviewing their IDA1 outcomes.

No historical IDA1 profit result exists yet. The reserve-market extension remains next after completing the intraday evaluation.
