# Data contract

No datasets are included yet. Keep downloaded raw data out of git unless redistribution is explicitly permitted.

For each source, record its URL, dataset identifier, licence/access terms, retrieval date, delivery period, timezone, native resolution, units and transformations.

Proposed tidy schema:

| Column | Meaning |
| --- | --- |
| timestamp_utc | Timezone-aware interval start |
| duration_hours | Actual delivery interval duration |
| zone | DE-LU or FR |
| price_eur_mwh | Day-ahead delivery price |
| demand_mw | Average power demand |
| wind_mw | Average wind generation |
| solar_mw | Average solar generation |

Validate unique zone/timestamp pairs, chronological order, gaps, interval alignment and numeric units. Preserve missing values for explicit treatment; do not silently fill them with zero. Do not mix forecasts and actuals without labelling them. Retain native resolution; document any duration-weighted aggregation.
