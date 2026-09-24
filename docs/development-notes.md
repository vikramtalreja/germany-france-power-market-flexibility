# Development notes: what we are doing and why

## 1. Price and fundamentals pipeline — completed

We aligned German and French prices with actual demand, wind and solar in UTC. This makes comparisons consistent and exposes missing hours before modelling. We retained the French autumn gap rather than invent data. See [fundamentals](../reports/fundamentals_2024.md).

## 2. December event case study — completed

We compared the German December peak with France and with other December weekday evenings. The purpose is to practise explaining market conditions with evidence. Actual fundamentals contextualise the event; they do not prove what traders knew or which network constraint was binding. See [case study](../reports/december_case_2024.md).

## 3. Perfect-foresight BESS benchmark — completed

We implemented a Pyomo mixed-integer model with HiGHS. A binary charging mode prevents physically inconsistent simultaneous charge/discharge. Energy balances account for losses. Daily starting and ending stored energy are equal, preventing artificial gains from draining initial inventory.

We solved each local day separately, including the 23-hour and 25-hour DST days. This matches the planned daily forecasting comparison. It restricts inter-day energy transfer; the annual sum is therefore a daily-constrained oracle, not the unrestricted annual optimum.

The main case uses 1 MW, 2 MWh, 90% round-trip efficiency and an illustrative EUR 10 per discharged MWh cycling cost. Costs are deliberately transparent and easy to change. December sensitivities test 85% efficiency and zero/EUR 20 cycling costs. No empirical battery life or investment-return claim is made.

Why this step matters: we need a feasible reference schedule and consistent financial accounting before attributing differences in returns to forecast quality. The reported oracle net margin is the comparison target under identical constraints and costs.

Validation: analytical arbitrage, flat positive prices, negative prices, both DST day lengths, and physical checks on all 732 daily dispatches. The full script ran successfully; notebook syntax was checked, but the notebook was not run in a Jupyter kernel.

See [benchmark report](../reports/battery_benchmark_2024.md) for the formulation, results, run metadata and limitations.

## 4. Simple forecast, fixed schedule, actual settlement — completed

Define the forecast issuance time and permissible historical data first. Build a transparent same-hour baseline, choose the battery schedule using that forecast, then evaluate it against actual prices. Keep the oracle's physical constraints, daily SOC restoration and cycling cost.

Compare MAE and event detection alongside net margin. Do not refit on the test period or use future actual fundamentals as inputs. Add ML only after the baseline passes information-timing checks.

This extends the thesis's economic evaluation of uncertainty into a market-facing experiment and connects Andreas's market understanding advice with Michael's emphasis on financial outcomes.

### Implementation and findings

Implemented latest-same-hour and seven-day-same-hour forecasts using complete delivery days D-8 through D-2. The chosen decision cutoff is D-1 at 09:00 local time. This deliberately conservative history avoids reliance on newer auction publication times; historical export vintages are not independently verified. DST days retain their real 23/25-hour durations. Repeated historical hours are averaged within a day and missing same-hours use the documented fallback/available-day mean.

The shared comparison starts on 9 January after the history window. We recompute the oracle on the same dates rather than comparing against full-year totals. Forecast prices choose quantities; actual prices settle them without re-optimisation. Realised losses remain in the sample. An oracle-dominance check verifies every daily comparison.

The seven-day baseline has lower MAE and higher net margin in both zones in this sample. That is an empirical result, not proof that error and financial value always rank models the same way. The fixed EUR 200/MWh spike threshold and negative-price diagnostics provide an additional view; they are not trading rules.

Validation includes future-data perturbation, constant forecasts, missing-history rejection, DST cutoff handling and an intentionally loss-making settlement example. Eleven tests pass. The Python workflow ran end-to-end; notebook syntax was checked, but no Jupyter kernel run is claimed.

See [forecast baseline report](../reports/forecast_baselines_2024.md) for results, assumptions, metrics and reproducible outputs.

## 5. Next: inspect failures, then define the ML evaluation — planned

Review loss days and missed extreme events to understand the baseline limitations. Before tuning ML, specify a chronological training/validation/test split and available features. Compare every model and the oracle on the same held-out dates. Do not describe 2024 as an untouched test year after using it for these retrospective analyses.

### Interpretation worth retaining

The seven-day average has worse spike recall than the latest-same-hour baseline in both zones, despite lower MAE and higher net margin. This shows that these metrics capture different aspects of performance. It does not establish that missing spikes is beneficial or identify a causal reason for the margin difference. A targeted event/dispatch attribution is the next analytical step.
