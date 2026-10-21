# From power prices to battery decisions
## A practical learning and presentation guide
Vikram Talreja | Germany–France power-market and BESS project | 21 October 2026

### The question behind the project
Does a more accurate electricity-price forecast actually lead to a better financial decision for a battery?

The project connects three things: understanding power markets, predicting prices, and deciding when a physically constrained battery should buy or sell electricity. It tests the complete chain instead of judging a forecasting model only by its average error.

### The three findings to remember
1. A lower average forecast error did not guarantee higher simulated battery margin. In the fixed 2025 comparison, the seven-day forecast earned more than the selected Random Forest in both markets.
2. The shape and timing of a forecast matter: a battery must have energy when prices are attractive and empty capacity when charging is attractive.
3. Operational assumptions matter too. Removing a forced nightly 50% charge reset increased simulated margin, mainly through lower purchase and cycling costs.

### Read this guide in three passes
First read chapters 1–6 for the market and battery concepts. Next read chapters 7–12 for the experiment and evidence. Finally read chapters 13–18 for intraday accounting, limitations, presentation practice and the glossary, then chapters 19–22 for the current roadmap and the auction-data execution plan.

### Where the project stands
Historical day-ahead analysis, forecast evaluation, ML diagnosis and continuous operation are completed. An incremental intraday optimisation and accounting engine is implemented and tested. Its current examples are synthetic: no historical intraday profitability result has been established. FCR/aFRR reserve optimisation is not implemented.

All money figures refer to simulated operating margins under stated assumptions. They are not investment returns, trading income or guarantees. See chapter 18 for the evidence map.
<!-- PAGE -->
# 1. The real problem and the project’s purpose
### Start with a familiar analogy
Imagine buying goods when they are cheap and selling them later. A battery can do something similar with electricity, but its warehouse is small, some energy is lost, and its charging and discharging speed is limited. Buying at a low price is useful only if enough capacity is free. A high selling price is useful only if stored energy is available.

An operator therefore needs more than a good price prediction. The operator needs a decision that respects the battery, the information available at that moment, and trades already made. A forecasting error at an unimportant hour may do little damage. An error that causes the battery to fill before the most negative-price hour can be expensive.

### Why this follows from your thesis
Your thesis coordinated building load, PV and EV charging using forecasts, uncertainty scenarios and receding-horizon optimisation. Its economic question concerned electricity-import costs and flexible charging. This portfolio moves the same decision-focused thinking into separate German and French market-price case studies.

The connection is methodological: forecast information changes an optimisation decision, and the decision is evaluated economically. The public project does not reproduce your confidential thesis code or data. Its current market controller is deterministic: it uses one forecast trajectory. It does not yet implement the thesis’s two-stage stochastic controller.

### The industry relevance
A forecasting analyst can improve a prediction. An optimisation analyst translates it into dispatch. A trader or portfolio manager asks whether the position is feasible, executable and financially useful. This project lets you explain how those responsibilities connect.

### A clear statement of your contribution
“I built a reproducible workflow that turns price forecasts into battery schedules and evaluates the financial consequences. I then examined why models earned different margins and whether operational assumptions were distorting the result.”

Do not claim a live trading strategy or experience running a real desk. Your demonstrated contribution is modelling, data handling, evaluation and diagnosis.
<!-- PAGE -->
# 2. Electricity markets without assumed background
### Why electricity has delivery times
Electricity production and consumption must remain balanced in real time. Contracts therefore specify where and when energy is delivered, for example a particular quarter-hour in a bidding zone. The same future delivery interval can be traded more than once before it begins.

A bidding zone is a market area with a common wholesale price for the relevant product. DE-LU means Germany–Luxembourg; France is another zone. Two batteries in our project are modelled separately. A price difference between the zones does not let a battery freely transfer electricity across the border.

### Three distinct stages
| Stage | Plain-language purpose | Project treatment |
|---|---|---|
| Day-ahead | Arrange tomorrow’s delivery before tomorrow starts | Historical forecast-to-dispatch experiments |
| Intraday | Adjust a position closer to delivery as information changes | Engine tested; historical study pending |
| Balancing | Help system operators manage real-time system imbalance | Not implemented |

An auction collects orders and clears them together. Continuous trading matches compatible buy and sell orders as they arrive. SIDC includes both continuous trading and intraday auctions. SDAC refers to the coupled European day-ahead mechanism. An auction result and a continuous-market price index are different products.

### A financial position is not a physical action
If you sell 1 MWh for an interval, you have a delivery obligation. Buying 1 MWh back later cancels that net obligation. The two cashflows remain even if the battery ultimately does nothing. Conversely, a battery’s physical schedule must match its net accepted position unless an imbalance is explicitly accounted for.

### Timing language
D means the delivery day; D-1 means the previous day. A gate closure is the deadline for the relevant trading opportunity. Our original D-1 09:00 forecasting cutoff is an experimental choice, not a claim about the exchange’s deadline. Always distinguish model timing from verified market rules.

Source for European intraday-auction structure: ENTSO-E IDA implementation [S1, chapter 18].
<!-- PAGE -->
# 3. Why prices rise, fall or become negative
### Merit order: a useful starting point
In a simplified competitive auction, offers are arranged from lower to higher price until demand is met. The marginal accepted offer helps determine the clearing price. Wind and solar often have low short-run marginal costs, so greater renewable output can reduce demand for higher-cost supply.

Real coupled auctions also involve network constraints, order structures and participant behaviour. A simple merit-order picture helps explain direction; it does not reconstruct the actual market-clearing algorithm or identify the exact generator responsible for a price.

### Why would a seller accept a negative price?
Supply can be difficult or costly to reduce. Some generators have shutdown and restart costs, minimum-output constraints, other obligations or support incentives. When supply is abundant relative to demand and flexibility/export options are limited, some sellers may prefer paying to produce over stopping. These are possible mechanisms, not causes proven for each hour by this project.

A negative wholesale price is not automatically a negative household bill. Retail contracts, network charges and taxes are separate. For the simulated battery, a purchase at a negative market price produces a positive energy cashflow, but efficiency, wear, fees and future discharge conditions still matter.

### Scarcity and congestion
A high price may reflect tight supply relative to demand, expensive marginal supply or constrained imports. High prices alone do not prove physical shortage. Congestion means a network limit restricts feasible transfers. Different zonal prices can be consistent with constrained trade, but the spread alone does not identify the binding constraint.

FBMC means flow-based market coupling: cross-border trades are assessed against a representation of network constraints. PTDFs describe how changes in zonal net positions affect monitored network flows; RAM is the capacity margin available to the market under that representation. The project has not implemented FBMC or used PTDF/RAM data to attribute price spikes.

### The right interview language
“Our observations are consistent with a mechanism” is defensible when you have prices and fundamentals. “We proved the mechanism caused the price” requires much stronger evidence.
<!-- PAGE -->
# 4. Germany and France: what our data actually shows
### Whole-year price observations: 2024
| Metric | DE-LU | France |
|---|---:|---:|
| Average price, EUR/MWh | 78.51 | 58.02 |
| Negative-price hours | 457 | 352 |
| Minimum, EUR/MWh | -135.45 | -87.29 |
| Maximum, EUR/MWh | 936.28 | 284.21 |

Germany had both a higher annual mean and more negative hours. There is no contradiction: a distribution can have a substantial negative tail and a high positive tail. An average hides timing and extremes that matter to storage.

### Residual load: define it before comparing it
Our residual load = demand minus wind minus solar. It is the demand left for all other sources and net exchanges. It does not subtract nuclear or hydro and is not a shortage measure.

In negative-price hours, mean residual load was 4.71 GW in Germany versus 31.46 GW in its nonnegative hours. France’s corresponding values were 32.20 and 42.39 GW. Solar output was higher on average in negative-price hours in both countries. These are associations, not controlled causal estimates.

### Why French residual load needs care
France has substantial nuclear generation. A residual-load calculation that subtracts only wind and solar still includes demand served by nuclear. Therefore France can have negative prices at a much higher measured residual load than Germany without that being paradoxical. Our data does not isolate nuclear inflexibility, support schemes or exports as the cause of specific negative hours.

National load definitions also differ. German national fundamentals are paired with DE-LU prices, so Luxembourg’s fundamentals are not included. Cross-country levels are not perfectly harmonised adequacy indicators.

### How to say it simply
“Renewable-rich, low-demand conditions were associated with negative prices, but the meaning of the remaining demand depends on the rest of each country’s generation mix.”

Evidence: price_comparison_2024.md and fundamentals_2024.md [R1].
<!-- PAGE -->
# 5. One event: Germany’s December price spike
### The observation
On 12 December 2024, 17:00–18:00 CET, the DE-LU price reached EUR936.28/MWh. France was EUR275.00/MWh at the same hour: a EUR661.28/MWh spread.

| Peak-hour quantity | Germany | France |
|---|---:|---:|
| Demand, GW | 68.04 | 70.49 |
| Wind, GW | 1.34 | 2.37 |
| Solar, GW | 0.03 | 0.19 |
| Residual load, GW | 66.67 | 67.92 |

For the other December weekdays at 17:00, German median residual load was 40.74 GW. The event’s 66.67 GW was unusually high in that matched comparison. Low wind alongside substantial demand is consistent with stronger reliance on other generation and imports.

### What the comparison improves
Comparing the same hour on other weekdays is more informative than comparing an evening winter event with all hours of the year. It partially controls for time of day and weekday status. It does not control for weather, holidays, outages or network conditions.

### What we cannot conclude
We did not identify a particular marginal generator, prove strategic bidding or calculate which network constraint bound. France’s similar residual load does not imply similar scarcity because its nuclear and other supply differs. Actual delivered wind and demand also do not reconstruct the information traders had at the preceding auction.

### Why this motivated the battery study
A small number of extreme hours may matter disproportionately to financial outcomes. The next question was whether forecasts lead a battery to hold energy for expensive hours and preserve empty space for cheap hours. The event study motivates that question; it does not itself prove battery profitability.

Presentation sentence: “I used a concrete event to connect market fundamentals with the value of flexibility, while separating the observed conditions from causes I could not establish.”

Evidence: december_case_2024.md [R1].
<!-- PAGE -->
# 6. Battery physics and the money calculation
### Power, energy and state of charge
MW is a rate; MWh is an amount. A 1 MW battery operating for 15 minutes exchanges 0.25 MWh. A 1 MW / 2 MWh battery has nominal two-hour duration at rated power; delivered usable energy also depends on efficiency and operating limits. State of charge (SOC) tells us how much energy is stored, here measured in MWh.

The historical model uses 90% round-trip efficiency, split equally between charging and discharging: each directional efficiency is the square root of 0.90, about 94.87%. Buying 1 MWh and later returning to the same stored-energy level permits about 0.9 MWh of discharge to the grid.

### The energy balance
SOC_next = SOC_now + efficiency_charge × charge_MW × hours − discharge_MW × hours / efficiency_discharge.

SOC must stay between 0 and 2 MWh; charging and discharging cannot each exceed 1 MW. The model prevents simultaneous charging and discharging. This matters particularly at negative prices, where an unphysical model could profit from deliberately wasting energy.

### A worked cycle
Buy 1 MWh at EUR50/MWh, then sell 0.9 MWh at EUR100/MWh. Purchase cost = EUR50; sales = EUR90. With EUR10 per MWh discharged cycling cost, wear = EUR9. Net operating margin = 90 − 50 − 9 = EUR31 before other costs.

For one grid-side MWh sold, the simple break-even sale price is approximately purchase price / 0.9 + 10. At EUR50 purchase price, this is EUR65.56/MWh, before fees. A positive price spread is not automatically enough.

### What the cycling charge means
The EUR10/MWh discharged term is an illustrative wear-cost proxy, not a detailed battery ageing model. Transaction fees concern trades; cycling costs concern physical use. Capex, financing, grid charges, taxes, auxiliary consumption, outages and detailed ageing are excluded from the principal historical results.
<!-- PAGE -->
# 7. Optimisation, forecasts and perfect foresight
### What an optimiser does
A forecast estimates future prices. An optimiser chooses actions given those prices and constraints. Our decision variables are charge, discharge and stored energy at each interval. Its objective is to maximise simulated revenue minus purchase expenditure and the included costs.

This is a mixed-integer linear programme (MILP). “Linear” means the objective and constraints are linear expressions in the variables. Binary variables select charging versus discharging modes. Pyomo expresses the mathematical model; HiGHS solves it. The solver is not a forecasting model and does not know tomorrow unless we give it tomorrow’s data.

### Why start with perfect foresight?
The perfect-foresight benchmark receives actual future prices. It asks what the same battery could earn with ideal price knowledge under the specified constraints. That provides a comparison bound, not an implementable forecast strategy.

A bound is valid only for matched constraints. A daily-reset oracle is not the right bound for a controller allowed to carry energy freely between days. The continuous experiment therefore solves a separate full-period oracle with the same initial and final inventory.

### Initial and terminal SOC
Initial SOC is stored energy at the start. Terminal SOC is the required energy at the end. Without comparable terminal treatment, one strategy could look better simply by selling its starting energy and leaving the battery empty. Equal starting and ending energy makes financial comparisons more meaningful.

The first experiments restore 50% SOC every day. Continuous operation removes that daily requirement but still matches the evaluation’s initial and final 1 MWh.

### Forecast then settle
First choose the schedule using forecast prices. Then freeze the quantities. Finally calculate their cashflows using actual prices. Do not reoptimise the forecast strategy with actual prices or cancel losing trades after observing the outcome. That would turn the backtest into hindsight.

Evidence: battery_benchmark_2024.md and forecast_baselines_2024.md [R1].
<!-- PAGE -->
# 8. Fair forecasting experiments
### Simple baselines before machine learning
The latest-same-hour baseline uses the most recent eligible historical value for that local hour. The seven-day baseline averages eligible values for that hour over seven historical days. For delivery day D, our conservative history is D-8 through D-2, at an experimental D-1 09:00 cutoff. “Yesterday” is therefore not an unrestricted input.

Ridge regression is a linear model that penalises large coefficients to reduce overfitting. Random Forest averages many decision trees and can learn nonlinear relationships. More complexity can help but does not guarantee better decisions.

### Features and leakage
Features are the inputs to a forecasting model. Here they include eligible price lags, seven-day price statistics, hour and weekday. Target-day actual demand, wind, solar and cross-market spreads are not used as forecast inputs. Those actuals are available for retrospective explanation, not necessarily before trading.

Leakage means allowing information from the future or evaluation set to influence a decision. Examples include normalising with future data, training on later dates, using a revised weather forecast as if it were an earlier vintage, or selecting the best model after seeing test results.

### Chronological evaluation
Training fits model parameters. Validation selects settings. Testing evaluates the frozen choice. Randomly shuffling time-series observations can mix future and past. Our 2024 evaluation is retrospective because that year had already been inspected. The original frozen-model 2025 transfer test used a previously uninspected period; later diagnosis and continuous-operation experiments on that same period are retrospective.

### Reproducibility
Save configuration, source hashes, package versions, chronological boundaries and chosen settings. A SHA256 fingerprint identifies exact file bytes; it does not prove the data is economically correct. Tests that perturb future inputs check that earlier forecasts do not change.

Evidence: ml-evaluation-protocol.md, ml_results_2024.md and independent_results_2025.md [R1].
<!-- PAGE -->
# 9. Accuracy and financial value are different scores
### What the metrics measure
MAE is mean absolute error, in EUR/MWh: the average size of a price prediction error. RMSE squares errors before averaging, then takes the square root; it penalises large errors more strongly. Neither metric directly knows how much the battery trades at each hour.

Margin depends on signed quantities, prices, efficiency and costs. An error at a large-volume discharge hour can matter more than several errors when the battery is idle. Forecast shape and the relative ranking of hours can influence dispatch more than the exact price level.

### Fixed 2025 comparison: 9 January–30 September
| Market / strategy | MAE EUR/MWh | Net margin EUR |
|---|---:|---:|
| DE-LU / seven-day mean | 27.31 | 55,361.95 |
| DE-LU / selected Random Forest | 25.39 | 52,715.33 |
| France / seven-day mean | 25.84 | 33,633.12 |
| France / selected Random Forest | 25.60 | 29,313.43 |

Both forests reduced average error relative to the seven-day forecast, but earned lower simulated margins: EUR2,646.62 less in DE-LU and EUR4,319.68 less in France. These comparisons use the same dates, battery and daily SOC constraints.

### What this does and does not establish
It establishes a mismatch between these accuracy and financial rankings. It does not prove that ML is generally inferior, that lower accuracy is desirable, or that the seven-day forecast will always win. Features were limited, models were frozen and did not retrain on 2025, and execution was simplified.

### Explain it to a nontechnical listener
“A weather forecast can be accurate on average yet miss the one storm that matters for a decision. Likewise, a price forecast can look good on average but put the battery in the wrong state when the valuable opportunity arrives.”

Evidence: independent_results_2025.md [R1].
<!-- PAGE -->
# 10. Diagnose the money, then inspect the actions
### Start with an identity
Net margin = sales revenue − purchase expenditure − cycling cost − included transaction fees.

To explain a difference, compare those components first. Preserve signed prices: buying at a negative price means negative purchase expenditure. Do not turn every purchase into a positive cost by taking absolute values.

### Random Forest minus seven-day mean, 2025
| Component, EUR | DE-LU | France |
|---|---:|---:|
| Sales revenue difference | -4,236.85 | -25,929.41 |
| Purchase expenditure difference | -1,445.91 | -19,434.93 |
| Cycling cost difference | -144.33 | -2,174.80 |
| Net margin difference | -2,646.62 | -4,319.68 |

The forests spent less on purchases and cycled less, but the sales reduction outweighed those savings. Accounting tells us where the difference sits; hourly forecasts, dispatch and SOC help explain the decision mechanism.

### Three concrete cases
France, 20 January: the RF forecast ranged roughly EUR98.49–106.20/MWh. That spread was insufficient to cover efficiency losses and the model’s cycling charge. RF stayed idle, while the seven-day strategy earned EUR604.92. This explains inactivity, not why the model learned that forecast shape.

Germany, 20 January: RF achieved a higher weighted selling price but discharged less energy. A good sale price alone did not compensate for lower volume.

Germany, 11 May: RF was almost full entering an extremely negative-price hour and could buy only about 0.108 MWh, while the baseline could buy 1 MWh. Empty capacity was valuable. In France on that date, RF preserved more charging headroom and outperformed, showing that the same model can succeed in another case.

We inspected five largest RF underperformance days and three outperformance days per market. These selected extremes illustrate mechanisms; they are not a representative sample. Reconstructed hourly schedules reconcile to original daily totals, but identical original solver tie-breaking cannot be proven.

Evidence: ml_diagnosis_2025.md [R1].
<!-- PAGE -->
# 11. Continuous operation: tomorrow inherits today
### The artificial daily reset
The first battery model starts and finishes each day at 1 MWh. This is convenient for comparing independent days, but it can force the battery to recharge at an unattractive time merely to satisfy a midnight condition.

The next version plans two local delivery days, commits only the first and revises the provisional second day later. It carries SOC across midnight and honours existing commitments. This is receding-horizon planning: repeatedly solve a future window, commit a portion, update the state, and solve again.

### Why current SOC is not tomorrow’s opening SOC
Suppose the battery holds 1.5 MWh at today’s decision time but has already promised to discharge later today. Tomorrow will not necessarily start with 1.5 MWh. The model projects current energy through the remaining committed physical schedule before planning tomorrow.

### Retrospective 2025 comparison
| Market | Daily reset EUR | Continuous EUR | Change |
|---|---:|---:|---:|
| DE-LU | 55,361.95 | 59,810.90 | +8.04% |
| France | 33,633.12 | 40,068.58 | +19.13% |

All cases start and end the evaluation at 1 MWh. France ends empty on all 264 internal boundaries; Germany does so on 257. Most of the gain is therefore associated with avoiding forced nightly recharging, rather than frequently carrying large amounts of energy overnight.

Germany reduced purchase expenditure by EUR7,441.04 and cycling cost by EUR467.41, offset by EUR3,459.50 lower sales. France reduced purchases by EUR5,736.46 and cycling by EUR393.26, with EUR305.75 higher sales.

Daily losses require inventory context: purchases today may enable sales tomorrow. Compare the full matched period rather than treating each day as an independent cycle.

Evidence: continuous_results_2025.md and continuous-operation-findings.md [R1].
<!-- PAGE -->
# 12. Sensitivity, uncertainty and model boundaries
### Sensitivity analysis asks “what if?”
The continuous experiment tested EUR1/MWh of transaction cost on each purchase and sale leg. Compared with daily-reset strategies reoptimised with the same fee, continuous margin remained higher by EUR4,620.26 in DE-LU and EUR6,444.08 in France. Fees can change decisions, not just subtract a fixed amount afterward.

The provisional horizon’s terminal target was also changed from 50% to 0% and 100%. Committed trajectories were identical in this experiment. This does not prove terminal treatment never matters: the forecast repeats the same hourly profile across both days, the battery is short-duration, and the final evaluation inventory is matched.

### What a perfect-foresight gap means
The matched continuous zero-fee oracle earned EUR66,394.25 in Germany and EUR47,503.54 in France. Forecast dispatch remained EUR6,583.35 and EUR7,434.96 below those bounds. This is a performance gap under a defined model, not a guaranteed recoverable commercial opportunity.

### Link back to stochastic optimisation
A deterministic controller uses one predicted trajectory. A scenario-based controller considers several possible futures. In a two-stage stochastic model, the first decision is common across scenarios because the future is still unknown; later recourse can depend on what happens. Scenario probabilities weight the expected objective.

VSS, the Value of the Stochastic Solution, compares stochastic optimisation with a consistently evaluated expected-value decision. EVPI, the Expected Value of Perfect Information, measures the benefit of knowing uncertainty in advance under matched assumptions. These ideas belong to your thesis methodology. The market project’s oracle gap should not automatically be called VSS or formal EVPI: it is not the same stochastic experiment.

### A question worth asking in an interview
“Which uncertainties matter most to this asset’s decisions, and how do you evaluate their economic impact?” That connects forecasting, optimisation and model validation without claiming a tool alone solves the business problem.
<!-- PAGE -->
# 13. Intraday: adjust a trade, do not erase it
### The key bookkeeping rule
Original day-ahead quantity and price stay in the ledger. Intraday adds another signed quantity at another price. The sum of positions must match physical delivery, or an imbalance must be explicitly represented.

Positive quantity means sell/export; negative means buy/import:

Cashflow = DA_price × DA_quantity + ID_price × ID_adjustment.

Physical net delivery = DA_quantity + ID_adjustment.

### One-interval example
You sold 1 MWh day-ahead at EUR100/MWh. Later you buy back 1 MWh intraday at EUR60/MWh. Original revenue remains EUR100 and the new purchase costs EUR60: net cashflow is EUR40 before fees. Net delivery is zero. Replacing the original sale with a zero-position row would wrongly erase the EUR40.

If you buy back at EUR140 instead, the same cancellation loses EUR40. An adjustment is not automatically beneficial just because it uses later information.

### Reversal needs more traded volume than physical power
If your original position is a 1 MWh purchase and you now want a 1 MWh sale, you must sell 2 MWh intraday: 1 cancels the purchase and 1 creates the sale. The battery still physically exports only 1 MWh. Trade volume and battery throughput are different quantities.

### What the new engine implements
It plans an adjustment using a forecast issued before the decision deadline; actual ID prices enter only settlement. It preserves the original window’s starting/ending SOC, keeps external commitments feasible, limits adjustment volumes, and handles 15-, 30- and 60-minute energy quantities. DA cashflows remain separate. New cycling cost follows revised physical dispatch.

It assumes all selected adjustments fill together, with perfect physical execution. This is an idealised price-taking auction model. Exchange lot sizes, bid curves, partial fills and continuous order-book behaviour are not implemented. Historical performance is not yet established.
<!-- PAGE -->
# 14. A synthetic intraday lesson you can calculate
### These prices are invented, not historical results
For transparent arithmetic only, this example uses 100% efficiency, no cycling cost and EUR1/MWh of intraday traded-energy fees. It has four one-hour intervals and the same nominal 1 MW / 2 MWh battery. The historical project uses 90% efficiency and a cycling charge.

| Interval | DA price | DA quantity | ID forecast | ID adjustment | Revised physical quantity |
|---|---:|---:|---:|---:|---:|
| 1 | 10 | -1 | 100 | +2 | +1 |
| 2 | 100 | +1 | 10 | -2 | -1 |
| 3 | 20 | -1 | 80 | +2 | +1 |
| 4 | 80 | +1 | 20 | -2 | -1 |

Prices are EUR/MWh; quantities are MWh. Original DA cashflow = -10 +100 -20 +80 = EUR150. The revised schedule starts and ends at 1 MWh and remains within physical limits. Eight MWh of ID trading costs EUR8.

### Outcome A: forecast materialises
ID cashflow = 2×100 − 2×10 + 2×80 − 2×20 = EUR300. Combined net = 150 +300 −8 = EUR442, an incremental EUR292.

### Outcome B: forecast is wrong
If ID actual prices instead equal [10, 100, 20, 80], the same ID positions generate EUR-300. Combined net = 150 −300 −8 = EUR-158, an incremental loss of EUR308. We do not cancel those trades after seeing the loss.

### What this demonstrates
The examples verify trade preservation, signed cashflows, forecast/settlement separation and downside risk. They estimate neither historical returns nor an attainable edge. The deliberately extreme invented prices and perfect fills make arithmetic easy; they do not establish market realism.

The source code and all 28 tests passed locally. Historical IDA1 data, publication timing, usable rights and execution assumptions still need to pass verification before a historical comparison is published.

Evidence: intraday_synthetic_demo.md and intraday-data-and-execution.md [R1].
<!-- PAGE -->
# 15. Data discipline and the remaining industry gap
### Data problems can masquerade as strategy profits
UTC timestamps prevent duplicate local clock labels from corrupting joins. A spring clock-change day can have 23 hours and an autumn day 25. Prices and energy must retain interval duration: a quarter-hour MWh observation is not the same number as average MW.

Our 2024 price coverage has 8,784 hours per zone. French actual fundamentals have one missing autumn hour, retained as missing rather than filled. The original German price export had two sequences; Sequence 1 was selected and later API prices matched it exactly, but original sequence metadata was not fully recovered. Cross-checking values is useful without claiming every metadata issue is resolved.

### Why intraday data needs extra care
An ID1 or ID3 index summarises trades over a window; it is not a firm quote executable at the start of that window. IDA1 instead names the first intraday auction. The current Energy-Charts price API is day-ahead only. SMARD intraday generation forecasts are not intraday prices.

We chose DE-LU IDA1 as the first historical target, but have not acquired a verified usable historical series. Before running it, require product identity, delivery intervals, price units, publication times, cancellations/missing-data treatment and permitted usage. Verify rules for the historical period. Website visibility alone does not establish redistribution rights or execution feasibility.

### What is close to industry practice
The project demonstrates chronological information handling, constrained optimisation, immutable trade accounting, economic evaluation, diagnostics and reproducibility. These are useful building blocks for an analyst supporting a trading or flexibility team.

### What remains absent
There are no executable bids, exchange order book, real liquidity calibration, partial fills, collateral/margin requirements, imbalance exposure, outages or production operations. Reserve capacity and activation are not modelled. Historical day-ahead results are simplified simulations; intraday is currently an engine and synthetic demonstration.

The next defensible claim is a documented historical auction benchmark after the data and execution requirements are satisfied, not “profitable cross-market trading.”
<!-- PAGE -->
# 16. Explain the project in five minutes
### Minute 1: problem and motivation
“Batteries can shift electricity between cheap and expensive periods, but they have limited power, capacity and efficiency. My question was whether a better price forecast actually produces a better financial decision. This follows from my thesis work on forecasting-aware EV/PV flexibility.”

### Minute 2: market context and method
“I compared Germany–Luxembourg and France, studied negative prices and a December spike, then modelled a separate 1 MW / 2 MWh battery in each market. I first established a perfect-foresight benchmark, then used forecasts to choose schedules and actual prices only to value those fixed schedules.”

### Minute 3: strongest forecasting result
“In the fixed 2025 comparison, Random Forest had lower average error than the seven-day forecast but earned less in both markets. I decomposed the gap into sales, purchases and cycling costs and inspected forecasts, dispatch and state of charge on selected days. Some forecasts flattened valuable spreads or left too little charging headroom.”

### Minute 4: operational modelling result
“I then removed an artificial daily 50% charge reset and preserved commitments across days. Simulated margin increased by about 8% in Germany and 19% in France, mostly through lower purchase and cycling costs. This showed that operational assumptions can be as important as model complexity.”

### Minute 5: intraday and honest boundaries
“I have implemented a tested incremental intraday engine that keeps original day-ahead trades intact and adds new trades. Its current examples are synthetic while historical data and execution assumptions are verified. I would next test one defined auction opportunity with credible information timing, rather than infer executable returns from a final price index.”

### Questions you should be ready for
Why not optimise on actual prices? That is the oracle, not a forecast strategy. Why did ML lose? Explain the observed dispatch mechanisms without claiming ML always loses. Are these profits? They are simulated operating margins with exclusions. Can this trade live? No: execution, risk, data and operational systems are missing.

Use the result appropriate to the experiment. Do not mix whole-year 2024, late-2024 ML and partial-2025 totals.
<!-- PAGE -->
# 17. Glossary and practice questions
| Term | Meaning in this project |
|---|---|
| BESS | Battery energy storage system |
| Arbitrage | Buy and sell across prices/times, subject to costs and constraints |
| Dispatch | Physical charge/discharge schedule |
| SOC / headroom | Stored energy / unused energy capacity |
| Residual load | Demand minus wind minus solar, by our definition |
| Spread | Difference between prices; specify the two markets or times |
| P&L / margin | Financial outcome; specify included and excluded costs |
| Price-taking | Assume our trades do not change the market price |
| Oracle | Perfect-future-information comparison under matched constraints |
| MPC / rolling horizon | Repeated optimisation with state updates and partial commitment |
| Leakage | Using information before it could have been known |
| Forecast vintage | A particular forecast version with its issue time |
| IDA1 / ID1 | First intraday auction / continuous-market index; not interchangeable |
| Imbalance | Difference between net contracted position and actual delivery |
| FCR / aFRR / mFRR | Frequency containment / automatic / manual restoration reserves |
| reBAP | German cross-control-area imbalance price; not a wholesale arbitrage price |

Reserve names explain the roadmap only. Their detailed historical product rules, qualification, capacity payments and activation settlement are not implemented here.

### Practise without looking at earlier pages
1. How much energy does 1 MW exchange over 15 minutes? Answer: 0.25 MWh.
2. Why can a negative-price purchase still be a poor decision? Capacity opportunity cost, fees, efficiency, wear and later prices can outweigh its immediate cashflow.
3. Sell 1 MWh at EUR100 DA, then buy it back at EUR60 ID: net delivery and cashflow? Zero MWh, EUR40 before fees.
4. Does zero error for an oracle demonstrate forecasting skill? No: actual future prices were supplied.
5. Why is the continuous experiment not another unseen 2025 test? That period had already been inspected.
6. What would disprove a claimed benefit? Matched evaluation showing the benefit disappears after credible costs, constraints, information timing or execution assumptions are applied.
<!-- PAGE -->
# 18. Evidence map and how to keep learning
### Repository: the source of project results [R1]
https://github.com/vikramtalreja/germany-france-power-market-flexibility

| Topic | Repository evidence |
|---|---|
| Prices and negative hours | reports/price_comparison_2024.md |
| Actual demand and renewables | reports/fundamentals_2024.md |
| December event | reports/december_case_2024.md |
| Battery formulation and benchmark | reports/battery_benchmark_2024.md |
| Baselines and failure analysis | reports/forecast_baselines_2024.md; forecast_failures_2024.md |
| ML evaluation and transfer | reports/ml_results_2024.md; independent_results_2025.md |
| Detailed ML diagnosis | reports/ml_diagnosis_2025.md |
| Continuous operation | reports/continuous_results_2025.md; docs/continuous-operation-findings.md |
| Intraday status and requirements | docs/intraday-data-and-execution.md |
| Synthetic ledger examples | reports/intraday_synthetic_demo.md |

Earlier reports retain their historical “next step” wording. The current README and roadmap indicate the latest completed stage. This guide describes the state on 21 October 2026.

### Primary external references checked for this extension
[S1] ENTSO-E, Intraday Auctions on SIDC: https://www.entsoe.eu/network_codes/cacm/implementation/ida/
[S2] Energy-Charts API specification: https://api.energy-charts.info/openapi.json
[S3] SMARD, Wholesale prices: https://www.smard.de/page/en/wiki-article/5884/5976/wholesale-prices
[S4] EPEX SPOT, Trading products: https://www.epexspot.com/en/tradingproducts
[S5] EPEX market results and EEX data products: https://www.epexspot.com/en/market-results and https://webshop.eex-group.com/offerdescription_eex_group_datasource

### A practical learning routine
Take one finding and explain it in three layers: a plain-language statement, the numerical evidence, then the assumptions that could change it. Recalculate the battery cycle and trade-cancellation examples by hand. Open one selected ML case and identify the forecast, action, SOC constraint and cashflow consequence. Finally, ask what information was actually available when that decision was made.

Your strongest story is not “I used many tools.” It is “I traced a prediction through a constrained decision into a financial outcome, checked the accounting, and investigated why the result occurred.”

<!-- PAGE -->
# 19. Agreed roadmap and the data we have checked
### Keep the project sequence coherent
| Stage | Question | Evidence status |
|---|---|---|
| Day-ahead benchmark | What is achievable with perfect knowledge? | Historical benchmark completed |
| Forecast-driven dispatch | Does accuracy create financial value? | Completed, including ML diagnosis |
| Continuous operation | Does value survive interday SOC decisions? | Completed with sensitivities |
| Day-ahead plus IDA1 | Can later information improve an existing position? | Synthetic engine tested; historical study pending |
| Energy plus reserves | How should battery capability be allocated? | Planned, not implemented |

Uncertainty-aware day-ahead optimisation is an optional research branch, not a replacement for this sequence. Price scenarios with a linear expected-profit objective can collapse to optimisation against their weighted mean. A risk-sensitive objective would be a separate experiment.

### What the sample files actually establish
The copied EPEX table contains 96 quarter-hour labels and 96 price rows for delivery on 22 October 2026. Its mean price is EUR146.82/MWh, consistent with its baseload index. It cannot be joined to 2025 day-ahead positions.

The ZIP sample contains German 15-minute auction prices and volumes for 20 February 2020 only. Its header is the legacy 15-minute call, not verified SIDC IDA1 history. Neither sample provides the requested continuous 2025 history. Sample layout is not proof of licensing rights, execution feasibility or historical coverage.

### Data request sent
A request has been sent to EPEX for all available DE-LU SIDC IDA1 history through the latest available date, with a separate 2025 quote, a current sample and clarification of research use and derived-publication rights. No purchase has been made. Raw licensed files must stay outside the public repository unless redistribution is explicitly permitted.

### What remains uncertain
Historical auction rules, available data periods, timestamp conventions, permitted use, predictor publication timing, fees and executable-order assumptions need validation. Nothing is collecting or backtesting historical intraday data in the background.
<!-- PAGE -->
# 20. What we will do when auction data arrives
### Step 1: Accept and document the source
Keep the original file unchanged in private storage. Record supplier, product, zone, retrieval date, coverage, file hash, timezone, units and licence. Confirm it is SIDC IDA1 rather than continuous ID1 or the legacy German auction. Obtain the applicable historical product specifications.

### Step 2: Validate delivery intervals
Convert timestamps to UTC while retaining local delivery labels and offsets. A local delivery day normally has 96 quarter-hours; daylight-saving transitions have 92 or 100. Check duplicate instants, missing intervals, cancelled auctions and non-numeric prices. Negative and zero prices are valid observations, not missing data. Never invent tradable prices by filling a cancelled auction.

### Step 3: Align the accepted day-ahead position
For our hourly 2025 day-ahead period, divide each hourly traded MWh quantity equally across its four quarter-hours and retain its original clearing price. The four quantities must sum to the original quantity, and their cashflows must sum to the original cashflow. Preserve the original DA ledger; do not re-optimise it after seeing ID prices.

### Step 4: Freeze the experiment before fitting
The existing comparison is 9 January to 30 September 2025. Earlier usable IDA1 history may support training and validation; later untouched history may support a fresh test after policy selection. Availability decides the feasible split. Already inspected 2025 DA outcomes make that comparison retrospective. Do not silently change dates to favour results.

### Step 5: Forecast before clearing
Begin with a transparent baseline such as the last available same-local-quarter IDA1 price, with an explicit DST policy. Only add rolling-average or DA-to-IDA spread models after the baseline works. Predictors must have been published before the decision; actual IDA1 clearing prices are reserved for settlement. On insufficient history or missing predictors, retain DA with no adjustment and record why.

### Step 6: Adjust, settle and compare
Start with the committed DA schedule and its boundary SOC. Optimise incremental ID trades using the forecast, then settle those trades at actual ID clearing prices under the stated fill approximation. Validate revised SOC, power and energy balance. Compare combined margin with the unchanged DA-only reference. Report harmful as well as helpful adjustments.

These steps are a documented implementation and evaluation plan. The canonical validator and DA quarter-hour adapter are now implemented and synthetically tested. A supplier-specific parser, forecasting pipeline and historical backtest still require suitable data.
<!-- PAGE -->
# 21. Execution assumptions and the evidence we will publish
### Decision timing and acceptance
The draft experiment uses one D-1 decision before the IDA1 gate. The existing January demo uses 14:30 local for a 15:00 local gate. Verify applicable historical rules, timezones and cancellations before using that timing across a dataset. No forecast may use later publication vintages.

The current engine assumes that all selected trades fill together at the auction price. Real auction acceptance depends on submitted orders and clearing; a clearing-price series alone cannot prove that our desired quantities would fill. Until valid bid sizes, price limits and acceptance logic are implemented, label the result a price-taking, full-fill simulation. Do not present it as executable trading P&L.

### Quantity limits and costs
Set explicit per-interval trade bounds before the evaluation. Show sensitivity to zero, restrictive and relaxed bounds, and to ID fees. Aggregate auction volume is contextual information, not a guarantee of available liquidity. Keep original DA fees fixed; charge ID fees on absolute incremental traded MWh and cycling cost on revised physical discharge. Report the assumed values beside every result.

### Acceptance checks before reporting historical margin
1. All original DA quantities, prices and cashflows remain unchanged.
2. Net DA plus ID quantity equals physical discharge minus charge energy in each interval.
3. SOC stays within bounds, power limits hold and starting/ending SOC match the comparison window.
4. Forecast inputs precede decisions, decisions precede gates, and settlement prices never enter planning.
5. Missing-data and cancellation cases follow a declared policy; excluded coverage is reported.
6. Gross cashflow less separately reported fees and cycling costs reconciles exactly to net margin.

### Result table and diagnostics
Publish DA-only margin, combined margin and incremental margin; ID buy/sell cashflows; ID traded MWh and fees; change in physical cycling costs; losing-adjustment days; worst daily adjustment; and coverage. Compare all strategies on matched intervals. Plot forecast versus actual prices, original versus revised dispatch, and SOC for the five worst and three best adjustment days. Include a no-adjustment control; perfect-ID foresight is an upper bound only.

### How the master guide stays current
The printable master lives in docs/printable/Power_Market_BESS_Project_Guide.pdf. Its editable source is docs/project-learning-guide.md. Every future project milestone must update the source, roadmap, development notes and status, then rebuild and visually inspect the PDF. Commit the source and PDF together. No unattended update process or data-acquisition job is implied.

Before printing, open docs/printable/README.md and check the revision date. Future revisions keep the same PDF filename so bookmarks remain useful.

<!-- PAGE -->
# 22. Intraday preparation v1: implemented and frozen
### What is now implemented
The canonical validator checks explicit timezone offsets, quarter-hour durations, duplicate instants, market and auction identity, numeric prices and coverage. Negative prices remain valid. Cancelled, missing, decoupled or unknown intervals make the whole day ineligible for adjustment; no price is filled. The coverage report records the private input file hash without copying prices into public results.

Tests cover 92-, 96- and 100-quarter-hour local days and reject ambiguous naive times. The DA adapter divides hourly energy and fees across four intervals, preserves price and constant power, interpolates SOC and reconciles each original trade. This is essential because 1 MW for 15 minutes is 0.25 MWh, not 1 MWh.

The paired evaluator checks physical feasibility and accounting before reporting margin, losing days, worst daily adjustment, traded volume, fees and cycling changes. A complete historical forecasting and evaluation run remains pending. The preparation suite passes 39 tests in total, including the existing model tests.

### Published facts versus our choices
EPEX's February 2025 brochure, PDF page 7, specifies the IDA1 gate at 15:00 CET/CEST, German quarter-hour products and a 0.1 MW volume tick. It gives nominal results from 15:20. This does not establish that every historical auction completed on time or that every requested trade filled.

Our simulation chooses a 14:30 decision, EUR1/MWh incremental trading fee and a 2 MW-equivalent adjustment cap per direction. The cap permits reversing a 1 MW position while physical battery power stays 1 MW. Full joint fills and continuous quantities remain idealisations. Actual fees, rule amendments and executable order acceptance remain open. Do not round schedules after optimisation: this can break physical feasibility.

### Frozen comparison
Version ida1-preparation-v1 fixes the 2025 retrospective dates, battery assumptions, previous-local-day same-quarter IDA1 forecast, fee and volume sensitivities, whole-day no-adjustment fallback and matched DA comparison. The reference day-ahead ledger is never repriced. Each daily adjustment keeps its original opening and closing SOC, so later DA commitments remain feasible.

A lower net margin is a valid result. Report negative outcomes and coverage, not only profitable days. Changes to the protocol require a new version and a statement of what results were already inspected. Later untouched tests require dates to be locked before looking at their price outcomes.

### Files to use
Execution: docs/intraday-data-and-execution.md. Frozen plan: docs/intraday-evaluation-plan.md. Parameters: config/intraday_evaluation_v1.json. Validation and accounting helpers: src/market_flex/intraday_data.py. Command-line validation: scripts/validate_intraday_data.py. Tests: tests/test_intraday_data.py.

Source: EPEX SPOT Trading Brochure, February 2025, pan-European Intraday Auctions section. The full source URL is recorded in the execution specification. Historical intraday profits and reserve optimisation remain unimplemented.
