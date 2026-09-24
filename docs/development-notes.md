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

## 4. Next: simple forecast, fixed schedule, actual settlement — planned

Define the forecast issuance time and permissible historical data first. Build a transparent same-hour baseline, choose the battery schedule using that forecast, then evaluate it against actual prices. Keep the oracle's physical constraints, daily SOC restoration and cycling cost.

Compare MAE and event detection alongside net margin. Do not refit on the test period or use future actual fundamentals as inputs. Add ML only after the baseline passes information-timing checks.

This extends the thesis's economic evaluation of uncertainty into a market-facing experiment and connects Andreas's market understanding advice with Michael's emphasis on financial outcomes.
