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

## 6. Loss days and missed extremes — completed before ML

We reconciled seven-day minus latest-same-hour margins using sales, purchases and cycling costs, then separated volume and transaction-price effects with an exact symmetric identity. This avoids assuming that smoothing or spike detection caused the improvement.

Net advantage: EUR 8,705.44 in DE-LU and EUR 8,215.20 in France. The seven-day strategy traded more energy. It obtained a higher weighted sale price in both zones; its weighted purchase price was higher in Germany but lower in France. Most interval-level advantage was booked in EUR 0–200 hours, but these regime contributions are not standalone profits because SOC links charging and discharge across regimes.

Despite missing 124 of 129 German spike classifications, the seven-day schedule discharged in 69 of those missed hours. In France it missed all 25 classifications but discharged in 14. Relative forecast prices can still produce useful actions without crossing the diagnostic threshold.

Worst seven-day loss cases: Germany, 11 February (EUR -33.92), with unexpectedly expensive charging; France, 20 April (EUR -39.77), with unexpectedly weak sale prices. In each case realised gross margin was positive but insufficient to cover cycling costs. The report includes the largest adverse hourly settlement surprises and complete selected schedules.

No forecasts were refitted. Accounting, paired-hour and decomposition checks passed. The notebook wrapper is syntax-checked; execution was validated through the script. See [failure analysis](../reports/forecast_failures_2024.md).

Next: define a chronological ML evaluation protocol before fitting a model. Treat stable daily shape and uneconomic cycling as hypotheses to test elsewhere, not proof of a causal mechanism or grounds to delete losing days.

## 7. Chronological ML protocol — specified before training

Initial training ends June 29; validation covers July 1–August 30. Final fitting uses targets through August 30; evaluation covers September–December with model parameters frozen and eligible historical features updated daily. These boundaries respect the D-2 policy at each initial cutoff.

We fixed a small Ridge/Random Forest search and calendar/historical-price features. Validation net battery margin selects the operational strategy; the MAE winner is tracked separately. Baselines may win. The already inspected 2024 window is retrospective; a proposed independent period still requires data verification.

Why: avoid deciding what success means after seeing ML results. The earlier publication attempt failed during automatic approval review due to a usage limit; this entry records the completed protocol publication attempt on 1 October 2026. See [protocol](ml-evaluation-protocol.md). Next is implementation, not an already completed ML result.

## 8. Ridge and Random Forest experiment — completed

Implemented the frozen protocol with calendar and historical-price features, training-only numeric scaling for Ridge, and four settings per ML family. Model parameters remain frozen during evaluation; eligible lag features update daily. The JSON max_features value is explicitly interpreted as float 1.0 (all features), matching the protocol rather than sklearn's integer-one-feature setting.

All validation candidates were scored and both zones' choices saved before evaluation began. The operational choice was the seven-day baseline in both zones. Family margin winners were Ridge alpha 0.1 and RF depth 6/leaf 5 in Germany, and Ridge alpha 10 and RF depth 6/leaf 20 in France. Validation MAE winners were additional deeper forests; their evaluation results are reported separately rather than used to change the selected strategy.

On September–December, the seven-day baseline earned EUR 21,664.33 in DE-LU and EUR 12,857.58 in France. Margin-selected RF earned EUR 20,022.09 and EUR 11,150.65, respectively, despite lower MAE: 35.09 versus 39.88 EUR/MWh in Germany, and 27.26 versus 28.46 in France. Ridge margins were EUR 21,493.00 and EUR 12,547.64. These are partial-period simulated margins after cycling cost, not annual revenue or full business profit.

Why this matters: we now have an observed example where lower forecast error produces worse financial decisions under identical battery constraints. The current result does not identify the specific forecast errors responsible, establish live profitability or prove that ML is generally inferior. It does justify keeping a strong baseline and evaluating decisions rather than MAE alone.

Validation: 15 tests pass, covering leakage perturbation, training-only preprocessing, cutoff boundaries, DST, financial near-tie selection and existing battery/settlement checks. All daily schedules obey physical and oracle-dominance checks. The Python experiment ran end-to-end; notebook syntax was checked without a Jupyter kernel run. Versions, hashes, selected parameters and training rows are recorded in the run audit.

See [ML report](../reports/ml_results_2024.md). Next freeze this result and assess robustness on verified uninspected data, or record a separately versioned experiment before adding features/refitting rules. Do not retune on September–December and relabel it a clean test.


## 9. Independent 2025 transfer test — completed

**Why:** the 2024 evaluation year had already been inspected. We needed a previously uninspected period to see whether the accuracy-versus-financial-value finding survived without retuning.

**What we froze:** January 9–September 30 2025 evaluation, original candidate list and operational seven-day baseline, original January 9–August 30 2024 training, existing information cutoff and battery assumptions. No 2025 fitting or strategy reselection. The protocol/runner were committed before acquisition; a unit-label whitespace correction was committed after the 2024 source check and before 2025 acquisition.

**Data verification:** the Energy-Charts API attributes these DE-LU and FR prices to Bundesnetzagentur | SMARD.de under CC BY 4.0. Both series exactly matched all 8,784 original 2024 hourly prices. The 2025 data passed exact hourly coverage checks. Each evaluation contains 265 days and 6,359 hours, handling the spring clock change. This supports product comparability without claiming every original export metadata ambiguity has been recovered.

**Findings:** seven-day averaging earned EUR55,361.95 in DE-LU and EUR33,633.12 in France. Previously margin-selected forests earned EUR52,715.33 and EUR29,313.43, while their MAE was lower (25.39 versus 27.31 in DE-LU; 25.60 versus 25.84 in France). Ridge earned EUR55,090.56 and EUR32,807.20. Seven-day averaging had one German loss day and two French loss days; French Ridge had only one loss day despite a lower total margin. Different objectives therefore give different rankings.

**Interpretation:** the financial advantage persisted in this fixed-model holdout, but this does not prove baseline superiority in general. ML models were deliberately not refreshed: this is transfer robustness, not a comparison with a continually retrained production system. The simulated margin excludes market execution, imbalance exposure, fees and capital costs.

**Evidence:** 15 existing tests pass. The new script completed 3,180 daily strategy schedules with unchanged-dispatch settlement, physical feasibility and oracle checks. Full metrics, daily/monthly results, paired comparisons, input/source fingerprints, and a chart are linked from the [2025 report](../reports/independent_results_2025.md).

**Profile use:** now describe a frozen, timing-aware evaluation that connects forecast error to battery decisions and checks robustness in another year. Avoid claiming live trading performance. A useful next industry extension is continuous SOC and a declared execution/fee model, under a new protocol and a fresh test period rather than tuning against this holdout.


## 10. Agreed progression to cross-market optimisation — 20 October 2026

Adopted the sequence: daily day-ahead benchmark → forecast-driven dispatch and ML diagnosis → continuous operation → day-ahead plus intraday → energy plus reserves. The [roadmap](roadmap.md) now records actual completion status, prerequisites and acceptance criteria; it supersedes earlier forward-looking entries as the current plan.

Why this order: first explain the existing forecast-to-margin finding. Then remove forced daily SOC restoration and track energy and trade commitments over time. Intraday trades must adjust an existing position while retaining its original cashflow. Reserve provision must share the same finite battery power and energy, so standalone revenues cannot simply be added.

The immediate deliverable is a retrospective RF-versus-seven-day diagnosis on existing 2025 results: full accounting reconciliation plus the five largest underperformance and three largest outperformance days per zone. No diagnosis results or continuous-operation results are claimed in this update.

Before implementing continuous operation, declare decision timing, horizon, forecast availability, initial/terminal treatment, costs and fair comparator. Before intraday/reserves, verify historical product rules, data timestamps and execution/activation assumptions. Existing inspected years remain retrospective for new experiments.

This update changes documentation only. No forecast, optimisation model or result has been rerun. The execution environment is currently unavailable; GitHub remains accessible for maintaining the roadmap. Previously reported test results belong to their original experiment runs.

## 11. ML diagnosis — daily stage completed, hourly stage blocked

On 20 October 2026, read committed daily 2025 results and frozen forest selections. Reconciled 530 paired daily differences and strategy totals using JavaScript. RF-minus-baseline gross margin is EUR-2,790.95 in DE-LU and EUR-6,494.49 in France; cycling-cost savings of EUR144.33 and EUR2,174.80 reduce the net shortfalls to EUR2,646.62 and EUR4,319.68. Selected five largest underperformance and three largest outperformance days per zone, retaining positive-margin underperformance and genuine RF wins.

Why: establish accounting evidence before assigning a behavioural explanation. Reduced cycling cost does not cause the shortfall. Daily data cannot separate sales from purchases or identify intraday timing mistakes.

The execution environment is unavailable and the original hourly dispatch CSV is git-ignored/not present in GitHub. Added a follow-through script that checks original hourly results against committed daily results, exports signed revenue/cost attribution and plots the 16 cases. That script has not been executed or runtime-tested. See [report](../reports/ml_diagnosis_2025.md). Continuous operation remains after completion of this hourly diagnosis.

## 12. Remote recovery route — prepared

Added a GitHub Actions job to reconstruct hourly dispatch without a local user installation. It downloads the four original public API responses, requires exact original response hashes, uses the frozen price-only training and model settings, and reconciles every daily financial total before publishing. It preserves the original experiment code and reports.

The full reconstructed dispatch and price inputs are saved as compressed CSV files under data/recovered, with an additional downloadable workflow artifact. Selected-case schedules, signed sales/purchase/cycling attribution and 16 charts are saved under reports. A separate hourly report is written only after successful checks. The original hourly file had no retained fingerprint, so matching daily totals does not prove identical solver tie-breaking; hourly explanations refer to reconstructed schedules.

Workflow success is not assumed by this entry: consult reports/recovery-status.json and the recovery audit. If a source hash, package installation or financial check fails, the job stops and does not publish unverified results.

## 13. Recovery and full hourly diagnosis — completed

The remote workflow succeeded on 20 October 2026: 15 tests passed, all four input response hashes matched, 76,308 hourly rows were reconstructed, and all 3,180 daily schedules reconciled (maximum net discrepancy about EUR1.14e-13). Python was 3.12.15 versus the earlier 3.12.14; recorded numerical library versions matched. Original hourly bytes had no fingerprint, so hourly conclusions refer to reconstructed schedules with matching daily outcomes.

Saved compressed full dispatch and public input price CSVs in data/recovered, plus a 90-day workflow artifact containing the uncompressed CSV. Added 16 four-panel case charts, selected hourly schedules and exact sales/purchase/cycling attribution. This removes the dependency on an ephemeral workspace for the diagnosis.

Findings: RF sales revenue was EUR4,236.85 lower in Germany and EUR25,929.41 lower in France; purchase savings and lower cycling costs partly offset these reductions. France January 20 had a narrow RF forecast range insufficient to cover losses/cycling, causing inactivity. Germany January 20 had higher weighted RF sale prices but less discharged volume. Germany May 11 RF entered the deepest negative-price hour almost full, while France May 11 RF preserved more charging headroom and outperformed. These demonstrate decision mechanisms without claiming why the model learned its forecast shape.

See [completed diagnosis](../reports/ml_diagnosis_2025.md). Continuous SOC with explicit commitments and terminal treatment is now the next stage. The original experiment configurations/results are unchanged, and the inspected 2025 period is not a new test set.
