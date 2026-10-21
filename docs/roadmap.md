# Repository roadmap: day-ahead analysis to cross-market optimisation

Agreed sequence: 20 October 2026. This roadmap is the current implementation order; older development-note entries retain their historical context.

| Version | Main question | Status |
| --- | --- | --- |
| Day-ahead benchmark | What is achievable with perfect price knowledge? | Completed under daily terminal-SOC constraints |
| Forecast-driven dispatch | Does forecast accuracy translate into financial value? | Completed, including detailed ML diagnosis |
| Continuous operation | Does the result survive realistic interday SOC decisions? | Completed; retrospective comparison and sensitivities |
| Day-ahead + intraday | Can later information improve an existing position? | First cross-market extension; pending data and execution specification |
| Energy + reserves | How should scarce battery capability be allocated? | Following extension; product selection and rules pending |

## 1. Day-ahead benchmark — completed

Implemented separate 1 MW / 2 MWh price-taking batteries in DE-LU and France using Pyomo/HiGHS, efficiency losses, power/energy bounds, mutually exclusive charging/discharging and equal daily initial/terminal SOC.

Evidence: [battery benchmark](../reports/battery_benchmark_2024.md). This is a daily-constrained perfect-foresight bound, not an unrestricted annual optimum or live trading income.

## 2. Forecast-driven dispatch — completed, including diagnosis

Implemented historical baselines, chronological Ridge/Random Forest evaluation and a fixed-model 2025 transfer test. Forecasts determine schedules; observed prices settle unchanged schedules. See [2024 ML results](../reports/ml_results_2024.md) and [2025 transfer test](../reports/independent_results_2025.md).

### ML margin gap diagnosis — completed

Completed on 20 October 2026: [full diagnosis](../reports/ml_diagnosis_2025.md), signed sales/purchase/cycling attribution, all 16 selected schedules and charts. Reconstructed hourly data reconciles with original daily results and is permanently retained under data/recovered. Continuous operation was subsequently completed; see stage 3.

- Compare the previously selected Random Forest against seven-day averaging separately in each zone, using the existing 2025 test outputs.
- Reconcile full-period and daily differences as sales revenue minus purchase expenditure minus cycling cost, with signed prices retained.
- Inspect the five largest RF underperformance days and three largest outperformance days per zone; rank by paired net margin and break ties by date.
- Plot forecast/actual prices, charge/discharge and SOC on a common timeline. Distinguish observed accounting differences from hypotheses about model behaviour.
- Explain missed extremes through battery actions and available SOC, rather than event classification alone.
- Keep models and original test results fixed. This is post-test diagnosis, not a new unseen evaluation.

Done when: a reproducible diagnosis script, full daily attribution, selected-case tables/plots, reconciliation checks and a short analyst report are committed. Add what we did, why, findings and limitations to development notes.

## 3. Continuous operation — completed

Purpose: remove the forced daily 50% SOC restoration and represent how today's decisions affect tomorrow's flexibility.

Completed on 21 October 2026. The [frozen protocol](continuous-operation-protocol.md), [results](../reports/continuous_results_2025.md), [interpretation](continuous-operation-findings.md) and [audit](../reports/continuous_audit_2025.json) document the implementation. All 20 tests passed; 101,744 hourly policy rows and 4,240 daily rows were checked. Zero-fee continuous margin increased by EUR4,448.94 in DE-LU and EUR6,435.47 in France. The two terminal-target sensitivities produced identical committed schedules. This inspected period remains retrospective. Intraday data/execution specification is now next.

The requirements below record the completed stage's scope and acceptance criteria.

Before running results, freeze a new experiment specification covering:
- Decision times, forecast issue times, planning horizon and which portion of a plan becomes committed.
- Forecast availability for every delivery interval in the horizon; no extension using future actual prices.
- State carried forward between decisions: physical SOC and existing delivery commitments.
- Initial SOC and terminal-energy treatment, including sensitivity to end-of-horizon incentives.
- Transaction-cost assumptions and accounting units, explicitly separate from cycling cost.
- Comparison dates and matched perfect-foresight benchmark with consistent initial/final energy and physical constraints.

Implementation requirements:
- Separate physical battery state, planned schedules, committed trades and financial settlement.
- Preserve interval duration in energy balances and transaction accounting, including DST.
- At each decision time, account for dispatch already committed before the new delivery window. Do not use current SOC as tomorrow's opening SOC without propagating those commitments.
- Commit only the tradable window; later planning intervals are provisional.
- Keep the daily-reset version reproducible as a reference.

Done when: boundary continuity, energy conservation, commitment feasibility, no simultaneous charge/discharge, future-data perturbation and cashflow reconciliation checks pass; a common-period comparison and terminal-condition sensitivity are documented. No claim that continuous operation must improve a forecast strategy.

## 4. Day-ahead + intraday — first cross-market extension

Purpose: evaluate whether later information can improve an existing day-ahead position.

Start with one zone and one explicitly defined intraday trading opportunity. Select the zone based on verified data availability rather than promising coverage of both.

Data prerequisite: document delivery intervals, transaction/quote timestamps, bid/ask or execution-price definition, available volumes, market access assumptions, historical rules, source licensing and coverage. Aggregated intraday indices support only a labelled illustrative benchmark unless a tradable execution interpretation is justified.

Implementation:
- Retain the original day-ahead transactions and prices in a trade ledger.
- Add intraday purchases/sales as incremental position changes; never overwrite the original trade.
- Separate financial positions from physical charging/discharging and reconcile the net delivery position.
- Define trading cutoffs, transaction costs, execution/fill assumptions and residual imbalance treatment.
- Compare against day-ahead-only operation with identical battery constraints and evaluation dates.

Done when: cancelling or adjusting a day-ahead position retains its original cashflow, no information is used before publication, execution assumptions are explicit, and incremental margin reconciles to the ledger. Publish examples of both beneficial and harmful adjustments.

## 5. Energy + reserves — following extension

Purpose: allocate limited battery power and stored energy between energy trading and reserve provision.

Choose one reserve product first (FCR or aFRR capacity) after verifying the rules for the historical market and period. Do not assume identical rules across countries or years.

Specify procurement timing, product duration, minimum bid size/aggregation assumptions, directionality, availability, response requirements, energy sustainability, activation, remuneration and non-delivery treatment.

Implement:
- Power headroom and energy/SOC feasibility throughout reserve commitments.
- Joint allocation with existing energy positions to prevent double-counting capacity.
- Separate capacity payments, activation-energy settlement, charging costs and degradation.
- Explicit activation scenarios or a documented approximation. Capacity-only studies must state how activation-related energy risk is treated.
- Add aFRR energy only after activation and settlement are represented.

Done when: commitments remain feasible under the declared activation assumptions and combined revenue reconciles without independently summing incompatible standalone strategies. Report opportunity costs, sensitivities and exclusions.

## Evaluation and documentation rules

- The inspected 2024 and January–September 2025 periods can support retrospective comparisons and diagnosis; they cannot be relabelled unseen tests.
- Freeze new choices before viewing new evaluation outcomes. Any claim of independent validation requires a verified, previously uninspected period.
- Keep historical configurations and results reproducible. Publish new experiments separately.
- Each stage includes the question, timing diagram or example where useful, assumptions, implementation, validation, findings, limitations and interview explanation.
- Describe only implemented market participation on the CV. Current implemented scope remains day-ahead arbitrage.

## Supporting work and deferred items

Completed: 2024 price/fundamentals pipeline, December event study, daily BESS benchmark, forecast baselines, baseline failure analysis, ML comparison and independent 2025 test.

Retained limitations:
- French actual fundamentals have one missing autumn hour, kept missing.
- The 2024 API source bridge exactly matches project prices; original export sequence metadata is not fully recovered.
- Actual fundamentals are retrospective context, not auction-time forecast features.

An educational PTDF/RAM network example and additional causal market investigations remain optional parallel learning work. They are not prerequisites for the agreed battery implementation sequence.
