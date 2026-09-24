# Forecast-Driven BESS Trading: Do Better Price Forecasts Create Better Financial Decisions?

Project direction recorded on 21 September 2026.

**Status:** this document is a reference brief, not a claim that the experiments below are complete. The 2024 price and actual-fundamentals analysis is implemented; the December case study is now completed; the perfect-foresight battery benchmark is now completed; forecasting experiments are next.

## Central question and project story

Do improvements in forecast accuracy translate into better financial decisions under explicit market and asset assumptions?

Forecasts should be evaluated both by prediction error and by the financial outcomes of the decisions they support. Better average accuracy does not necessarily imply better financial results; the project will test this rather than assume a particular winner.

Planned project story:

> I am building a Germany–France power market case study to evaluate forecasts not only by prediction error, but by the simulated realised financial outcomes of the battery schedules they produce.

Once the relevant experiments are complete, this can become:

> I built a Germany–France power market case study to evaluate forecasts not only by prediction error, but by the realised financial outcomes of the battery schedules they produce.

Here, “realised” means evaluated against observed historical prices in a simulation, not live trading income.

Suggested future repository names: `forecast-driven-bess-trading` or `germany-france-bess-market-analytics`. These are naming options only; the current repository remains the project location.

## Connection to Andreas, Michael and the thesis

| Input | Project response |
| --- | --- |
| Andreas: understand Germany and France, price formation, scarcity and cross-border constraints; proactively explain events | Market case studies with charts, supporting evidence and explicit limits on causal conclusions |
| Michael: combine forecasting, automation and financial evaluation; pay attention to extreme events | Compare forecast accuracy with battery margins, missed spikes and negative-price detection |
| Michael: Python, SQL and reporting | Reusable Python pipeline, later a small SQL database and a reporting dashboard |
| Thesis: forecasts, residual-based scenarios, deterministic versus two-stage stochastic control, economic metrics, VSS and EVPI | Extend experience in the economic value of uncertainty-aware building control into a market-facing battery experiment |

The thesis abstract reports reduced import costs from stochastic control in matched cases. It does not by itself demonstrate trading-desk P&L or that a less accurate forecast produced better returns. VSS and EVPI refer to the thesis's particular optimisation problem. A simple forecast-driven battery comparison should not be labelled a VSS experiment without the required stochastic formulation and matched benchmarks.

## MVP implementation order

### 1. December price-spike case study

**Goal:** explain observed market conditions and investigate why prices moved.

Start with 10–14 December 2024 and the German price peak on 12 December, 17:00 CET. Plot German and French day-ahead prices, demand, wind, solar, residual load and the DE-LU minus France spread. Identify the top 20 high-price hours over a clearly stated period and inspect negative-price periods separately.

Compare peak conditions with a defined baseline. Produce hourly spreads and daily mean spreads with labelled units and timezones. Write a short analyst note separating observations from hypotheses requiring outage, forecast or network evidence. A spread alone does not demonstrate congestion or an FBMC mechanism.

### 2. Perfect-foresight BESS benchmark

**Goal:** estimate the maximum arbitrage margin achievable under the chosen model assumptions using known actual prices.

| Parameter | Starting assumption |
| --- | --- |
| Power | 1 MW |
| Energy | 2 MWh |
| Round-trip efficiency | Sensitivity range 85–90%; select and record one main-case value |
| Initial state of charge | 50% |
| SOC bounds | 0–100% of modelled usable capacity |
| Degradation | Explicit EUR/MWh throughput assumption |
| Charge/discharge | Mutually exclusive |
| Terminal SOC | Equal to initial SOC for matched fixed-horizon comparisons |

Specify separate charge and discharge efficiencies whose product equals round-trip efficiency. Define whether throughput means discharged energy or total charge plus discharge; avoid accidentally double-counting degradation.

Model each bidding zone separately. Document optimisation horizon, timestep, fees, grid constraints and excluded costs. The result is a model-specific upper bound, not a guarantee of achievable revenue or whole-project profitability.

### 3. Simple forecast benchmark

**Goal:** optimise with forecast prices and evaluate the resulting schedule with actual prices.

Candidate baselines:

- Latest available same-hour price profile.
- Average of the same delivery hour over the last seven available days.

Replace vague “tomorrow equals yesterday” wording in code with explicit delivery timestamps and an information cutoff. Handle 23-hour and 25-hour local delivery days correctly.

Use identical battery constraints, initial and terminal conditions and evaluation periods for every strategy.

### 4. Machine-learning forecast

Add ML only after the baseline and financial accounting work.

Candidate models: linear regression, Random Forest, and optionally XGBoost. Model complexity is secondary to a valid comparison.

Candidate features: lagged prices, hour, weekday, weekend/holiday indicators, lagged DE–FR spreads, and demand/wind/solar/residual-load forecasts available at the decision time.

**Do not use future actual demand, wind, solar, residual load or the target hour's actual cross-border spread as predictors.** Historical forecast exports may contain revisions: check issue times and forecast vintages before treating them as available information.

Use chronological training, validation and held-out testing or walk-forward evaluation. Fit preprocessing and select models on training/validation data only. If December is used to guide development, do not also describe it as an untouched test.

### 5. Financial evaluation

Populate this table only after comparable backtests exist:

| Model | MAE (EUR/MWh) | Spike detection / capture | Negative-price detection | Realised gross margin | Margin after degradation and fees | Gap to perfect foresight |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | Pending | Pending | Pending | Pending | Pending | Pending |
| ML forecast | Pending | Pending | Pending | Pending | Pending | Pending |
| Perfect foresight (oracle) | 0 by construction | Oracle, not a prediction score | Oracle, not a prediction score | Pending | Pending | 0 |

Define a high-price threshold using training data or a fixed declared threshold. Distinguish forecast event detection (precision/recall) from the battery's financial capture of those events. Include worst daily result, cycling and sensitivity to efficiency/degradation where useful.

Calculate the gap against the same objective: net margin versus net-margin oracle, not net margin versus gross revenue.

## Critical rule: decision information and settlement

The experiment must follow:

1. A forecast exists before the declared decision cutoff.
2. The optimiser creates a feasible battery schedule using that forecast.
3. Actual prices become known.
4. The fixed schedule is evaluated against those actual prices.

For the MVP, explicitly model a schedule committed before the day-ahead auction with simplified price-taking execution assumptions. Document the assumed acceptance of scheduled quantities and exclusions such as bid rejection, liquidity, market impact and imbalance exposure. This is not a simulation of continuous intraday order-book execution.

A schedule optimised after day-ahead prices are published answers a different operational question. Optimising against future actual prices belongs only to the perfect-foresight benchmark.

Gross simulated margin is the sum of actual price multiplied by net discharged energy. Subtract declared degradation and fees separately. Do not call this complete business profit when capital costs and other operating costs are excluded.

## What hiring teams should be able to inspect

| Capability | Evidence |
| --- | --- |
| Market understanding | Germany–France event chart and analyst note using demand, renewables, residual load and spreads |
| Modelling | Battery formulation with SOC, efficiency, power, terminal energy and degradation assumptions |
| Financial thinking | Forecast comparison showing whether lower error actually improves simulated financial outcomes |
| Reproducibility | Python pipeline, documented data quality, chronological evaluation and later SQL/reporting |

## CV wording — use only after completion

- Built a forecast-driven BESS trading case study for Germany–France power markets, comparing baseline and machine-learning price forecasts by both prediction accuracy and simulated realised battery arbitrage returns under identical SOC, efficiency and degradation constraints.
- Evaluated whether lower forecast error translated into better financial decisions by feeding each forecast into a battery optimiser and evaluating dispatch against actual day-ahead prices.
- Analysed high-price and negative-price periods using demand, renewable generation, residual load and cross-border spreads to investigate price movements and flexibility value.

## Interview wording — use only after completion

> I wanted to test a practical question relevant for trading and flexibility teams: does a better forecast actually lead to a better financial decision? I compared simple and machine-learning price forecasts, used each forecast to optimise a battery schedule, and evaluated the simulated realised return against actual prices. This helped me look beyond MAE and focus on financial outcomes, especially during price spikes and negative-price periods.

## Immediate tasks and existing work

The original brief proposed creating the repository, README and price pipeline first. Those are already complete; do not restart them.

- [x] Repository and README created.
- [x] Germany and France 2024 price data loaded and compared.
- [x] Actual demand, wind, solar and residual load aligned with prices.
- [x] Plot December day-ahead prices and fundamentals.
- [x] Produce a clearly scoped top-20 high-price-hour table.
- [x] Produce hourly and daily DE-LU minus France spread outputs for the case study.
- [x] Write the event explanation and unresolved evidence questions.
- [x] Build the perfect-foresight battery benchmark.
- [ ] Add simple forecasts, then ML and financial evaluation.

See [fundamentals results](../reports/fundamentals_2024.md) for current limitations, including one missing French actuals hour, national-versus-bidding-zone coverage and pending German price-sequence metadata confirmation.

First establish the market story, then add the battery, then forecasting. Keep ancillary services, reBAP imbalance-cost analysis, SQL/reporting and educational FBMC modelling as later extensions rather than prerequisites for this MVP.

December milestone: [completed report and reproducible outputs](../reports/december_case_2024.md).

Battery milestone: [daily perfect-foresight results and assumptions](../reports/battery_benchmark_2024.md). Main case: 90% round-trip efficiency, EUR 10/MWh discharged cycling cost, daily initial/terminal SOC 50%. Next: a simple forecast with information-cutoff checks.
