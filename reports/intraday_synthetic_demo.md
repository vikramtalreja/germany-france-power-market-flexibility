# Incremental intraday trades: synthetic accounting demonstration

**Not historical market performance.** Four invented hourly intervals, a 1 MW / 2 MWh battery, deliberately 100% efficiency and zero cycling cost for hand calculation. Main historical experiments retain 90% efficiency and EUR10/MWh discharged cycling cost. ID transaction fee is EUR1/MWh traded. All fills and perfect execution are assumed.

Original invented DA prices: [10, 100, 20, 80] EUR/MWh. DA buys 1 MWh, sells 1, buys 1, sells 1: cashflow = -10 +100 -20 +80 = EUR150. Battery starts/ends at 1 MWh.

New pre-auction forecast: [100, 10, 80, 20]. Revised physics sells, buys, sells, buys. This requires incremental trades [+2, -2, +2, -2] MWh, not [+1, -1, +1, -1]: each adjustment first cancels the original position and then reverses it. Physical power stays within 1 MW. Eight MWh of trading incurs EUR8 fees.

| Invented outcome | Original DA cashflow EUR | ID cashflow EUR | ID fees EUR | Combined net EUR | Change from DA-only EUR |
|---|---:|---:|---:|---:|---:|
| Forecast materialises | 150 | 300 | 8 | 442 | +292 |
| Forecast wrong: original price shape returns | 150 | -300 | 8 | -158 | -308 |

The **same planned quantities** are settled against each invented outcome. The losing adjustment is not cancelled with hindsight. Actual clearing prices never enter planning. Original DA transactions remain identical in both ledgers; revised physical dispatch determines cycling costs when enabled.

The lesson is an accounting identity and forecast risk, not an estimate of achievable intraday revenue. Settlement cashflows are not price times revised physical delivery at a single market price. A trade can offset an earlier commitment without requiring its own separate physical battery cycle.

Outputs: [summary](intraday_synthetic_summary.csv), [ledger](intraday_synthetic_ledger.csv), [dispatch](intraday_synthetic_dispatch.csv). The engine supports quarter-hour durations, constrained adjustment volumes and normal efficiency/cycling parameters; tests verify these separately. See [data/execution requirements](../docs/intraday-data-and-execution.md). Historical DE-LU IDA1 evaluation awaits verified data and execution assumptions.
