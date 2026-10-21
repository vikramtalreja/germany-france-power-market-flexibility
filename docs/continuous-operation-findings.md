# Continuous operation: findings and interview explanation

## What we did and why

The original model required the battery to return to 1 MWh (50% SOC) at every midnight. That makes days independently comparable but can force purchases just to restore inventory. We removed that daily requirement, carried actual model state between days, and projected the next delivery day's opening SOC through already committed dispatch. The optimiser plans two local delivery days, commits only the first, and replans the second later.

The seven-day forecast and battery physics remain unchanged. The same issuance-time forecast profile is repeated across both planning days: the longer horizon does not add predictive information. All strategies start and finish the evaluation with 1 MWh, preventing a free-inventory advantage. See the [frozen protocol](continuous-operation-protocol.md).

## What the results say

9 January–30 September 2025; separate 1 MW / 2 MWh batteries. Values are simulated operating margins after EUR10/MWh discharged cycling cost, before investment costs. The main comparison has no transaction fee.

| Market | Daily reset EUR | Continuous EUR | Change EUR | Change % |
|---|---:|---:|---:|---:|
| DE-LU | 55,361.95 | 59,810.90 | +4,448.94 | +8.04% |
| France | 33,633.12 | 40,068.58 | +6,435.47 | +19.13% |

The gain is not mainly evidence of storing energy overnight. France ends empty at all 264 internal boundaries; Germany ends empty at 257, and carries 0.103 or 0.949 MWh at the other seven. Every final evaluation state is restored to 1 MWh. The model largely benefits from no longer being forced to restore 50% SOC every night.

### Accounting explanation

Differences are continuous minus daily reset, calculated from the retained hourly dispatch. Negative purchase/cycling differences are savings. Signed negative-price purchases are preserved.

| Market | Sales revenue change EUR | Purchase expenditure change EUR | Cycling cost change EUR | Net margin change EUR |
|---|---:|---:|---:|---:|
| DE-LU | -3,459.50 | -7,441.04 | -467.41 | +4,448.94 |
| France | +305.75 | -5,736.46 | -393.26 | +6,435.47 |

Net change = sales change minus purchase expenditure change minus cycling cost change. Germany discharged 46.74 MWh less and France 39.33 MWh less. More trading volume was not necessary to earn a higher simulated margin. These are accounting mechanisms, not a separately identified causal attribution of each optimisation choice.

### Sensitivities and bounds

An illustrative EUR1/MWh transaction fee on each buy/sell leg leaves gains of EUR4,620.26 in DE-LU and EUR6,444.08 in France against fee-matched daily-reset strategies. Both strategies are reoptimised with the fee; the comparison is not just a fee subtracted after dispatch.

The provisional second-day terminal targets of 0%, 50% and 100% produce exactly identical committed charge, discharge and SOC trajectories in this run. Their provisional second-day plans need not be identical. Do not conclude that terminal treatment never matters: the repeated forecast profile, short-duration battery and chosen horizon limit what this sensitivity demonstrates.

The full-period zero-fee perfect-foresight bounds are EUR66,394.25 in DE-LU and EUR47,503.54 in France. Continuous forecast dispatch remains EUR6,583.35 and EUR7,434.96 below those bounds. The bound now matches continuous initial/final constraints; the older daily-constrained oracle is not the appropriate bound for this version.

### Daily examples need inventory context

Germany's largest daily improvement is 1 July (+EUR333.21); its largest daily decline is the final day, 30 September (-EUR104.23), which starts empty and restores the required final 1 MWh. France's largest daily improvement is the first day, 9 January (+EUR99.75), which starts with 1 MWh and ends empty. Its largest decline is 31 May (-EUR54.15), starting and ending empty. Initial/final inventory effects make standalone daily profit claims misleading. Use matched full-period results, and inspect [selected hourly cases](../reports/continuous_case_dispatch_2025.csv) before explaining any individual action.

## Validation and practical limits

All 20 tests passed in [the successful workflow](https://github.com/vikramtalreja/germany-france-power-market-flexibility/actions/runs/39621103976). Full-run checks reconcile the old daily baseline, preserve commitments, enforce SOC/energy continuity and exclusive charging/discharging, protect forecast availability, reconcile signed trade cashflows and compare every policy with its fee-matched global oracle. There are 101,744 hourly policy rows and 4,240 daily rows. See the [audit](../reports/continuous_audit_2025.json).

The 2025 period was already inspected. This is a frozen retrospective structural experiment, not independent validation. Price-taking, full acceptance and perfect physical execution remain assumptions. There are no actual bids, bid/ask spreads, outages, imbalance costs, intraday trades or reserve commitments. Historical hourly resolution is retained for this period. The terminal sensitivity did not change committed actions here; results should not be generalised to other forecasts, durations or horizons.

## How to explain it in an interview

“I first compared forecasts by the financial outcomes of their battery schedules. Then I tested whether an artificial daily 50% charge reset was influencing those outcomes. I implemented continuous state of charge, projected the opening state through existing commitments, and separated committed trades from settlement. Margin improved mainly through lower purchase and cycling costs. That taught me to inspect operational constraints and accounting as carefully as forecast accuracy.”

A defensible CV addition: “Implemented rolling two-day BESS planning with continuous SOC, existing-commitment projection and a separate day-ahead trade ledger; validated energy and cashflow consistency and quantified sensitivity to transaction fees and terminal targets.”

## Next: one intraday extension, after data verification

The state and ledger foundation is now implemented. Before claiming day-ahead plus intraday optimisation, choose one market and one trading opportunity using verified timestamped prices/quotes and volumes. Document when information is available, execution price and fill assumptions, delivery resolution, fees, cutoffs and residual imbalance treatment. An aggregated intraday index alone supports only an explicitly illustrative benchmark unless tradable execution can be justified.

Keep original day-ahead cashflows intact. New intraday trades must be incremental signed positions whose sum remains physically feasible. Compare against the same day-ahead-only policy and dates. This is the next milestone, not a completed strategy.
