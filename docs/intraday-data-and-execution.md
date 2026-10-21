# Intraday data verification and execution specification

Checked 21 October 2026. Target: DE-LU, one IDA1 auction adjustment after the day-ahead auction and before delivery. **Status: accounting/optimisation engine implemented and tested; historical intraday backtest not run.** All numerical intraday examples currently published are synthetic.

## Sources checked and what they establish

| Source | Verified finding | Consequence |
|---|---|---|
| Energy-Charts OpenAPI, https://api.energy-charts.info/openapi.json | Price endpoints are day-ahead; `/price` has bidding zone and date parameters, not an intraday product selector. DE-LU/FR day-ahead data is attributed to SMARD under CC BY 4.0. | Existing project price downloads cannot supply intraday settlement. API licensing must not be extended to other website datasets. |
| SMARD wholesale-price explanation, https://www.smard.de/page/en/wiki-article/5884/5976/wholesale-prices | Visualised wholesale prices are day-ahead prices. | Intraday generation forecasts on SMARD are not intraday electricity prices. |
| ENTSO-E IDA implementation, https://www.entsoe.eu/network_codes/cacm/implementation/ida/ | IDAs launched 13 June 2024. IDA1 closes D-1 15:00, IDA2 D-1 22:00 and IDA3 D 10:00 for noon onward. | IDA1 is a defined first extension; do not confuse IDA1 with the continuous-market ID1 index. |
| EPEX trading products, https://www.epexspot.com/en/tradingproducts | Auction and continuous products are distinct; trading procedures/product specifications are exchange-specific. | Preserve product, zone, resolution and date-specific rules. |
| EPEX market results, https://www.epexspot.com/en/market-results | Public indexed results exist; the requested DE-LU 2025-01-09 IDA1 page was not retrievable in this session. Indexed pages warn that commercial data use needs approval. | No complete historical series, usable-data rights or execution metadata has been acquired/verified. This is an access finding, not proof that data is unavailable anywhere. |
| Energy-Charts spot-price website, https://www.energy-charts.info/charts/price_spot_market/chart.htm?c=DE&l=en | Site lists intraday auction/continuous series, but retrieved HTML is a JavaScript shell. | No validated historical download or usage terms for those intraday series established. |
| EEX Group data offering, https://webshop.eex-group.com/offerdescription_eex_group_datasource | Official market-data products include historical information and bid/ask data. | A candidate acquisition route; no subscription purchased or credentials requested. |

No historical ID prices have been substituted with day-ahead prices or generated values. The synthetic examples are deliberately separate from historical outputs.

## Why auction first

A single auction adjustment gives a clear decision deadline, a forecast before clearing and a single clearing-price settlement per delivery product. Continuous SIDC requires timestamped executable bid/ask prices, order depth, fill/latency assumptions and repeated decisions. An ID1/ID3 weighted trading index is an ex-post summary, not a firm quote available throughout its calculation window. Optimising against a final index and treating it as known earlier creates look-ahead and execution bias.

## Implemented accounting model

For interval t, signed export quantities are positive sales and negative purchases:

- Original accepted position: q_DA(t), at original p_DA(t).
- Incremental intraday trade: delta_q_ID(t), at p_ID(t).
- Net physical delivery: q_DA(t) + delta_q_ID(t) = (discharge_MW - charge_MW) * interval_hours.
- Gross cashflow: p_DA(t) * q_DA(t) + p_ID(t) * delta_q_ID(t).
- Net margin: gross cashflow minus original DA fees, ID fees and cycling cost of the revised physical dispatch.

Original DA cashflows are fixed when planning ID. The optimiser uses only a pre-decision ID forecast and does not receive actual ID clearing prices. Revised physical dispatch preserves the original window's starting and ending SOC so commitments outside the window stay feasible. All intervals must be contiguous, future and timezone-aware; 15-, 30- and 60-minute energy accounting is supported. Hourly DA power can be expanded into four quarter-hours, but a historical adapter must allocate each hour's energy correctly and retain original prices.

Buy/sell adjustment bounds are explicit input limits in MWh per interval. They are not inferred from aggregate market volumes. No simultaneous ID buy/sell or physical charge/discharge is allowed. A reversal from a 1 MW purchase to a 1 MW sale requires 2 MW equivalent trading volume, although physical power remains 1 MW.

## Explicit simplifications

- All selected adjustment orders are assumed accepted together at actual auction clearing prices, with perfect physical execution. This is not a demonstrated exchange-fill model or an implemented basket order.
- Quantities are continuous; minimum order size, quantity ticks and valid bid curves are not yet implemented. No historical tradability claim is made.
- Fees are illustrative inputs; EUR1/MWh of absolute ID traded energy in the demo. Physical cycling cost remains separate.
- No residual imbalance is charged because the accepted net position exactly equals the physical schedule. Partial fills and outages would invalidate that assumption and need explicit treatment.
- One pre-delivery adjustment window only; no repeated intraday decisions, order book, market impact, cross-border battery arbitrage or reserves.
- Demo timing uses D-1 14:30 local decision and 15:00 local gate in January, expressed in UTC. Forecast timestamps are validated but real publication vintages are not available.

## Historical-data acceptance checklist (still open)

Before a historical run, acquire a permitted dataset and record exact source, retrieval time, response/file SHA256 and permitted use/redistribution. Require:

1. Zone, venue and auction ID, delivery start/end with UTC offsets, price EUR/MWh, resolution and auction status.
2. Publication timestamp or defensible publication-availability evidence for every predictor; a download timestamp is not a publication vintage.
3. A forecast issued before the chosen decision; actual ID clearing prices must remain settlement-only.
4. Full date coverage, DST handling, duplicates, cancellations, decoupling, missing-price rules, and matching DA intervals. Do not forward-fill cancelled auctions as tradable prices.
5. Date-specific auction rules, lot sizes and order acceptance assumptions; quantify the price-taking/full-fill approximation.
6. Executable-volume limits or clearly labelled sensitivity bounds; aggregate auction turnover is not accessible liquidity for this battery.
7. Frozen evaluation dates and forecasting policy before inspecting outcomes. Already inspected DA dates may support retrospective comparison only.

The next historical run must compare retained DA-only cashflows with combined DA+ID cashflows, use identical initial/final SOC, and publish both helpful and harmful adjustments. There is no historical ID profit result to report yet.

## Reproduce current implementation

`PYTHONPATH=src python -m unittest discover -s tests` (39 passing tests at preparation v1).
`python scripts/demo_intraday.py` creates clearly labelled synthetic ledger, dispatch and summary CSVs.
See [synthetic demonstration](../reports/intraday_synthetic_demo.md), [status](../reports/intraday_stage_status.json), `src/market_flex/intraday.py` and `tests/test_intraday.py`.

## Sample review and next-data protocol

The October 2026 copied table and February 2020 ZIP sample do not supply the required 2025 SIDC IDA1 history. A broader historical-data enquiry has been sent; no subscription purchased. See chapters 19–21 of [the master guide](project-learning-guide.md) for source acceptance, timestamp checks, immutable DA allocation, forecast cutoffs, missing-data policy, matched settlement evaluation and the execution assumptions still requiring historical verification.

## Execution specification v1: verified references versus simulation assumptions

Rechecked 21 October 2026 against EPEX SPOT Trading Brochure **February 2025**, pan-European Intraday Auctions section (PDF page 7):
https://www.epexspot.com/sites/default/files/2025-02/EPEX%20SPOT%20Trading%20Brochure%202025%20February.pdf

The brochure specifies IDA1 gate D-1 15:00 CET/CEST, nominal results from 15:20, German 15-minute contracts, volume tick 0.1 MW, price tick EUR0.01/MWh, and price limits -9999/+9999 EUR/MWh. These are dated reference specifications; the brochure does not establish every exception, operational delay or rule revision across the study period. Confirm date-specific amendments with supplier specifications before an executable-strategy claim. ENTSO-E's IDA page also publishes cancellation and decoupling notices: https://www.entsoe.eu/network_codes/cacm/implementation/ida/.

Our decision at 14:30 is a deliberate 30-minute buffer, not the exchange deadline. `auction_timing` constructs it in Europe/Berlin before converting to UTC, including delivery days adjacent to clock changes. `check_information` rejects predictor publication or forecast issuance after the decision. A saved publication timestamp is needed; retrieval time is insufficient.

**Finalised simulation v1:** one pre-delivery adjustment, original DA ledger immutable, original daily boundary SOC fixed, full joint acceptance assumed, continuous quantities, EUR1/MWh illustrative ID fee, base trade bound 2 MW equivalent per direction (0.5 MWh per quarter-hour). This is a research relaxation. Fees, available liquidity, actual order acceptance and date-specific operational exceptions remain unverified, not silently finalised as facts. No order submission is implemented.

See [frozen evaluation plan](intraday-evaluation-plan.md) and `config/intraday_evaluation_v1.json` for fixed sensitivities, reporting and fallback policy.

## Canonical data interface and validation

Required CSV columns: `delivery_start`, `delivery_end` (offset-aware ISO8601), `zone` (= DE-LU), `auction` (= IDA1), `price_eur_mwh`, `status`. Allowed status: cleared, cancelled, missing, decoupled, unknown. Optional `volume_mwh` is nonnegative context, not accessible liquidity. Missing rows are counted; no rows or prices are fabricated. Unknown product/status conventions must be mapped explicitly in a supplier adapter.

`python scripts/validate_intraday_data.py PRIVATE.csv --start 2025-01-09 --end 2025-09-30 --report PRIVATE-coverage.json`

The report contains source SHA256, coverage and daily eligibility, not raw price data. It does not certify licensing or execution. Whole-day eligibility requires every expected interval to be cleared with a finite price. DST grids contain 92/96/100 quarter-hours; repeated local clock labels remain different UTC instants. Never silently localise naive autumn timestamps.

`expand_da_quarterhours` checks original physics, allocates energy/fees and interpolates SOC, then reconciles original cashflows and quantities by source interval without modifying the source frame. `evaluate_adjustment` validates paired physics and accounting before producing incremental financial metrics.
