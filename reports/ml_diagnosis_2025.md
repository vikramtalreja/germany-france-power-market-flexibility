# Random Forest margin diagnosis — 2025

## Scope and execution status

Daily accounting and deterministic case selection completed from committed results. Hourly revenue/purchase decomposition and forecast/price/dispatch/SOC charts are pending execution: the original git-ignored hourly dispatch file is not available through GitHub, and the execution environment was unavailable on 20 October 2026. No hourly explanations are inferred from daily totals.

Compare the original validation-margin-selected forest (DE-LU: rf_depth_6_leaf_5; FR: rf_depth_6_leaf_20) with seven_day_same_hour over 9 January–30 September 2025. This is retrospective diagnosis of the inspected holdout, with no retuning or reselection.

## Full-period accounting

All differences below are RF minus baseline. Gross margin equals signed sales revenue minus signed purchase expenditure. Net margin equals gross margin minus cycling cost.

| Market | Gross margin difference, EUR | Cycling cost difference, EUR | Net margin difference, EUR | Discharged energy difference, MWh |
|---|---:|---:|---:|---:|
| DE-LU | -2790.95 | -144.33 | -2646.62 | -14.43 |
| FR | -6494.49 | -2174.80 | -4319.68 | -217.48 |

RF's lower cycling cost partially offsets its gross-margin shortfall. It does not explain the shortfall: DE-LU gross margin was EUR2,790.95 lower, offset by EUR144.33 lower cycling cost; France gross margin was EUR6,494.49 lower, offset by EUR2,174.80 lower cycling cost. France's RF discharged 217.48 MWh less across the period. This establishes lower activity, not why its forecasts chose that activity or whether every extra baseline cycle was profitable.

RF outperformed on 103 German days and underperformed on 154 (8 effectively tied), versus 86 and 164 French days (15 tied), using EUR0.000001 as the daily tie tolerance. The results are not a universal rejection of ML.

## Selected days

Five largest negative paired differences and three largest positive paired differences per zone; chronological date breaks exact ties. Selection uses net margin, not whether RF itself lost money.

| Market | Case | Date | Baseline net, EUR | RF net, EUR | Difference, EUR | Discharge difference, MWh |
|---|---|---|---:|---:|---:|---:|
| DE-LU | underperformance 1 | 2025-01-20 | 1028.88 | 639.79 | -389.09 | -1.90 |
| DE-LU | underperformance 2 | 2025-01-21 | 368.26 | 167.64 | -200.61 | -1.95 |
| DE-LU | underperformance 3 | 2025-04-27 | 407.65 | 213.80 | -193.85 | -0.95 |
| DE-LU | underperformance 4 | 2025-05-11 | 627.67 | 439.58 | -188.09 | 0.05 |
| DE-LU | underperformance 5 | 2025-02-14 | 317.25 | 132.00 | -185.25 | -2.85 |
| DE-LU | outperformance 1 | 2025-06-30 | 279.77 | 405.84 | 126.07 | 1.90 |
| DE-LU | outperformance 2 | 2025-08-05 | 109.20 | 219.49 | 110.29 | 1.80 |
| DE-LU | outperformance 3 | 2025-06-01 | 111.57 | 187.54 | 75.98 | -0.90 |
| FR | underperformance 1 | 2025-01-20 | 604.92 | 0.00 | -604.92 | -3.79 |
| FR | underperformance 2 | 2025-02-17 | 236.99 | 0.00 | -236.99 | -3.70 |
| FR | underperformance 3 | 2025-01-15 | 277.95 | 48.05 | -229.90 | -3.70 |
| FR | underperformance 4 | 2025-01-21 | 204.85 | 0.00 | -204.85 | -3.79 |
| FR | underperformance 5 | 2025-01-17 | 148.33 | -17.79 | -166.12 | -1.99 |
| FR | outperformance 1 | 2025-05-11 | 139.35 | 247.01 | 107.66 | -2.70 |
| FR | outperformance 2 | 2025-07-07 | 5.84 | 88.08 | 82.24 | -0.05 |
| FR | outperformance 3 | 2025-05-10 | 181.13 | 254.36 | 73.24 | -1.05 |

### Supported interpretations

- **France, January 20, February 17 and January 21:** RF daily margin and discharged energy are zero, while the baseline earns positive margin. Given equal starting/ending SOC, losses and no simultaneous operation in the existing model, these are idle RF days within numerical tolerance. The hourly forecasts are needed to explain why the optimiser chose inactivity.
- **France, January 17:** RF loses EUR17.79 while the baseline earns EUR148.33. Lower cycling cost does not rescue its worse realised gross margin.
- **Germany, January 20:** RF earns positive EUR639.79 but trails the baseline by EUR389.09 and discharges 1.90 MWh less. Relative underperformance is not an outright loss.
- **Germany, May 11:** RF discharges slightly more and earns less gross margin. Lower activity cannot explain every adverse case.
- **France, May 11:** RF earns EUR80.66 more gross margin while saving EUR27.00 in cycling cost; its net advantage is EUR107.66. More cycling is not always better.
- **Germany, June 30:** RF's EUR145.05 gross advantage exceeds its EUR18.97 extra cycling cost, leaving EUR126.07 more net margin.

## What the daily data cannot resolve

Gross margin is sales minus purchases. Daily gross totals cannot uniquely identify those two components. We cannot yet say that RF bought too expensively, sold too cheaply, discharged too early, or missed a particular price extreme. Those require the unchanged hourly schedules and prices; no causal model-behaviour claim is made here.

## Hourly follow-through

Run `python scripts/diagnose_ml_2025.py` with the original `data/processed/independent_dispatch_2025.csv`. The script verifies hourly settlement against the committed daily results before exporting separate signed sales/purchase/cycling differences, the 16 selected schedules and four-panel charts (actual/forecast prices, charging, discharge, SOC). It does not refit or optimise. If the hourly file is missing, recover it from the original workspace or reproduce the frozen evaluation using its documented inputs and check reconciliation; do not substitute fabricated schedules.

The script has been added but not executed or runtime-tested in this session. Its hourly outputs are therefore not claimed as results.

## Evidence

- Inputs: [daily results](independent_daily_2025.csv), [aggregate metrics](independent_metrics_2025.csv), [frozen selections](ml_selection_2024.json).
- Outputs: [paired daily accounting](ml_diagnosis_daily_2025.csv), [selected cases](ml_diagnosis_cases_2025.csv), [totals](ml_diagnosis_totals_2025.csv).
- Checks executed in JavaScript against retrieved CSV contents: 265 matched dates per strategy/zone, daily gross-minus-cost reconciliation and agreement of strategy net totals with published aggregate metrics.

Interview wording supported now: “The selected forests' lower simulated margins came from lower gross trading margin, partly offset by reduced cycling cost. French RF even remained idle on several days when the baseline traded profitably. Hourly diagnosis is needed to separate buy-price, sell-price and timing effects.”
