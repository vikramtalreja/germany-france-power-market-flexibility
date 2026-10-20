# Random Forest margin diagnosis — completed

Recovery and hourly analysis completed on 20 October 2026 through [GitHub Actions](https://github.com/vikramtalreja/germany-france-power-market-flexibility/actions/runs/39464466134). No local installation or user upload is required.

## What was verified

Four public API responses match the original SHA256 fingerprints exactly. The frozen models and unchanged optimiser regenerated 76,308 hourly strategy rows; all 3,180 daily schedules reconcile with the original published results, with maximum net-margin discrepancy about EUR1.14e-13. All 15 existing tests and the additional hourly physical/accounting checks passed.

The original hourly file had no retained hash, so this is a reconstruction validated against daily results, not proof of byte-identical original dispatch where solver ties exist. Hourly findings below refer to reconstructed schedules. This is retrospective diagnosis of the already inspected 2025 period; models were not retuned.

## Why RF earned less overall

Differences are RF minus seven-day averaging for the original validation-margin-selected forest in each market.

| Contribution to net difference | DE-LU, EUR | France, EUR |
|---|---:|---:|
| Change in sales revenue | -4,236.85 | -25,929.41 |
| Benefit from lower purchase expenditure | +1,445.91 | +19,434.93 |
| Benefit from lower cycling cost | +144.33 | +2,174.80 |
| **Net margin difference** | **-2,646.62** | **-4,319.68** |

RF spent less on buying energy and cycling, but the reduction in sales revenue was larger. This mixes price and volume effects; it does not mean RF always received a worse unit sale price. In fact, several cases show better average sale prices but insufficient traded volume.

## What the hourly evidence explains

### France: narrow forecast spreads sometimes make inactivity optimal

On January 20, RF forecast prices between EUR98.49 and EUR106.20/MWh; seven-day averaging forecast EUR107.34–188.04/MWh. At 90% round-trip efficiency and EUR10/MWh discharged cycling cost, buying at EUR98.49 requires a sale price above roughly EUR119.43/MWh to cover these costs for a complete cycle. Even the RF forecast maximum is below that threshold. With equal starting/ending SOC, inactivity is therefore economically consistent with its forecast.

Actual prices offered valuable opportunities: the baseline earned EUR604.92 while RF earned zero. RF also stayed idle on January 21 and February 17. This explains the forecast-to-decision mechanism in these cases; it does not establish why the forest learned that compressed price range.

### Germany: selecting a higher sale price can still earn less

On January 20, RF's weighted sale price was EUR487.86/MWh versus EUR448.48 for the baseline. But RF discharged only 1.90 MWh versus 3.79 MWh. At 08:00, actual price was EUR431.99/MWh and both batteries began the hour full; the baseline discharged 1 MW while RF held its energy. RF's eventual higher average sale price did not compensate for lower activity: net margin was EUR389.09 lower.

This is a direct example of why neither MAE nor weighted sale price alone measures strategy value.

### Germany: filling too early can miss deeper negative prices

On May 11 at 13:00, actual price was EUR-250.32/MWh. RF began the hour at 1.897 MWh SOC, leaving only enough capacity to charge about 0.108 MWh from the grid. The baseline began at 0.949 MWh and charged 1 MWh. RF's weighted purchase price was EUR-23.98/MWh versus EUR-72.78 for the baseline. The purchase-side disadvantage outweighed RF's slightly higher sales revenue; net margin was EUR188.09 lower.

The important mechanism is the timing of available storage headroom, not merely identifying a negative-price hour.

### RF wins demonstrate the reverse mechanism

In France on May 11, RF bought at a weighted EUR-106.46/MWh versus EUR-20.05 for the baseline, while cycling less. At 15:00, when actual price was EUR-109.84, RF had room to charge 1 MW while the baseline charged only 0.108 MW. RF earned EUR107.66 more net margin. In Germany on June 30, additional discharge revenue outweighed extra purchase and cycling costs, producing EUR126.07 more margin.

These observations support an asset-specific explanation: preserve energy for valuable sale hours and headroom for valuable charging hours. They do not establish a general rule that less cycling, more cycling or one model family is superior.

## All selected cases and charts

The five largest underperformance and three largest outperformance days per market are documented in [the full hourly report](ml_diagnosis_hourly_2025.md), with forecast and actual prices, charging, discharging, SOC, signed cashflow contributions and missed-spike actions. Individual hourly cashflows are not standalone profits because energy links hours.

- [All 530 paired daily comparisons](ml_diagnosis_daily_2025.csv)
- [16 selected cases](ml_diagnosis_cases_2025.csv)
- [Hourly selected-case CSV](ml_diagnosis_selected_dispatch_2025.csv)
- [Sales/purchase/cycling totals](ml_diagnosis_sales_purchase_totals_2025.csv)
- [Daily hourly-reconciled attribution](ml_diagnosis_hourly_reconciled_daily_2025.csv)
- [Recovery audit](dispatch_recovery_2025.json)
- [Full compressed dispatch and source price CSV files](../data/recovered/README.md)

## Interview explanation and next step

“I found that the financial gap depended on dispatch decisions. On some French days the forest predicted too little spread to justify cycling, so the battery stayed idle despite profitable actual opportunities. On a German negative-price day it filled too early and had little space left at the lowest price. I reconciled the differences through sales, purchases and cycling costs and retained examples where the forest outperformed.”

The next stage is continuous operation: carry SOC and existing commitments across days, specify terminal-energy treatment and transaction costs, and compare under consistent assumptions. The daily 50% SOC reset remains in all results here. New experiments on these inspected periods are retrospective, not fresh holdout tests.
