# Continuous operation — frozen experiment specification

This protocol and configuration are committed before running the experiment. The January 9–September 30 2025 period is already inspected; this is a retrospective structural sensitivity comparison, not an unseen test.

## Question

Does carrying energy across days change forecast-driven battery margin, losses and dispatch compared with the daily 50% SOC reset?

Use the existing seven-day baseline only; no ML tuning. Retain 1 MW / 2 MWh, 90% round-trip efficiency and EUR10/MWh discharged cycling cost. Use verified recovered prices and record their fingerprints.

## Decision sequence and commitments

At D-1 09:00 local, previous commitments for D-1 remain fixed. Project the battery's SOC from the state at that cutoff through the remaining committed D-1 dispatch to D 00:00. This is deterministic under the explicit perfect physical execution assumption; do not use future realised prices to calculate projected energy.

Optimise delivery days D and D+1 together using only information available at that cutoff. Commit the entire D schedule once. D+1 is a provisional plan and can change at the next auction decision. Preserve a transaction ledger of the committed D energy quantities, distinct from physical SOC and from later actual-price settlement. No intraday trades are implemented in this stage.

At the first decision, assume SOC is already 1 MWh and the battery remains idle until the first evaluation delivery; there are no earlier commitments. All later projected initial states come from the preceding day's committed schedule.

The experiment assumes price-taking quantities are accepted in the day-ahead auction and dispatch is delivered perfectly. It does not implement price-dependent order acceptance, outages or imbalance settlement.

## Forecast information

Construct an equal-day-weighted same-hour profile from the complete seven local delivery days D-8 through D-2. Apply that *same issuance-time profile* to both planning days. Do not call a D+1 forecast that includes newer historical observations unavailable at D-1 09:00.

Use UTC for joins, local dates for decision/horizon boundaries. Spring/fall days retain 23/25 hours. Hourly energy equals power multiplied by an explicit one-hour interval duration; this version rejects other resolutions. The repeated-profile assumption adds foresight horizon, not new predictive information.

## Terminal assumptions and costs

Main scenario: provisional end-of-horizon SOC fixed at 1 MWh. Sensitivities fix provisional end SOC to 0 or 2 MWh. These are planning targets, not daily reset constraints. Only actual committed dispatch moves SOC.

All scenarios have physical initial and final evaluation SOC fixed at 1 MWh. On the last delivery day, shorten the planning horizon and impose that common final SOC, overriding provisional terminal sensitivities. This avoids counting liquidation of initial inventory as a gain.

Fee sensitivity: EUR1/MWh on each charging and discharging market leg, in both optimisation and settlement. This is an illustrative execution-cost assumption, not a sourced market fee. Compare to daily reset reoptimised with the same fee.

## Comparators and gates

1. Reproduce the original seven-day daily-reset results at zero fee and reconcile every day with published daily results.
2. Run fee-matched daily-reset comparators.
3. Solve full-period perfect foresight for each fee with the same initial/final energy, efficiency and operating constraints. This is a global bound, not a rolling-horizon forecast. Require optimal termination; a time-limited feasible solution must not be labelled an optimum.
4. Test SOC continuity at midnight, forecast future-data perturbation, preserved prior commitments, physical constraints, signed transaction cashflow, and oracle dominance. The previous daily-constrained oracle remains a distinct historical result.
5. Report full-period and monthly margins, loss days, fees, discharged energy, daily boundary SOC, forecast-versus-realised accounting and comparisons. Daily net losses are accounting windows, not independent cycles when SOC is carried across days.
6. Record frozen config/code/input fingerprints and run versions. No strategy selection from these sensitivities.

## Interpretation

Continuous operation need not outperform the daily-reset policy under imperfect forecasts and terminal assumptions. Finite horizons can shift decisions and produce end effects. Explain these through actual boundary states and committed actions, not only aggregate margin.

This establishes state/commitment accounting for the later day-ahead-plus-intraday extension. It does not itself demonstrate cross-market trading.
