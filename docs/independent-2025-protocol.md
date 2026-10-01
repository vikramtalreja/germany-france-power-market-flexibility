# Frozen independent 2025 evaluation

Frozen before downloading or inspecting 2025 prices or performance. This is a historical, previously uninspected project holdout, not a live trading trial.

## Question and fixed decisions
Does the seven-day baseline's 2024 financial advantage persist? Evaluate 9 January–30 September 2025, inclusive, separately for DE-LU and France. January 1–8 supplies history only. Stop before the October 2025 transition to quarter-hour day-ahead products. No tuning, replacement of candidates, new features, clipping, or 2025 model fitting.

Use exactly the evaluation candidates in `reports/ml_selection_2024.json`, plus perfect foresight. Reconstruct ML estimators deterministically using the unchanged `config/ml-evaluation.json` and original January 9–August 30 2024 training sample. This tests transfer of the existing models; their age is a limitation, not a reason to silently refit. Keep seven-day averaging as the preselected operational strategy for both zones regardless of the new ranking.

Use existing calendar/lagged-price features and D-1 09:00 local decision cutoff, with complete D-8 through D-2 history. No contemporaneous actual generation, demand, or future cross-border prices. The price history updates each day; model coefficients do not.

Battery: 1 MW / 2 MWh, 90% round-trip efficiency, daily initial and terminal SOC 50%, EUR10/MWh discharged degradation, no simultaneous charging/discharging. Optimise forecast prices; settle unchanged dispatch using observed prices. Perfect foresight is an upper bound only under these same daily constraints.

## Data and acceptance gates
Fetch official Energy-Charts `/price` data for DE-LU and FR, attributed by that endpoint to Bundesnetzagentur | SMARD.de under CC BY 4.0. Cache original JSON, retrieval time, exact URL and SHA256. Verify EUR/MWh units, non-null finite prices, unique increasing UTC interval starts and exact hourly coverage of local delivery dates. Reject unexpected resolution; do not aggregate or impute.

Before scoring 2025, compare 2024 API prices timestamp by timestamp with the existing 2024 project series. Require all 8,784 hourly timestamps and absolute difference at most EUR0.011/MWh per zone. Stop if this source bridge fails and document the mismatch without scoring 2025. Matching supports numerical comparability; it does not recover every detail of the original export's Sequence metadata.

## Reporting, without reselection
Report each fixed model's MAE, RMSE, net operating margin after degradation, oracle gap, loss days, worst day, spike (>EUR200/MWh) and negative-price detection. Include monthly margin and paired daily net differences versus seven-day averaging. Describe reversal or persistence of ranking without claiming statistical certainty. Record input/code hashes and gate outcomes. No claim of realised live trading P&L, out-of-sample financial guarantee, or deployability: bids, liquidity, imbalance exposure, fees, outages, capex and continuous SOC operation remain outside scope.

## Reproduction
Run `python scripts/evaluate_2025.py`. Cached API inputs are reused. API rate-limit errors stop acquisition; respect Retry-After before retrying. Freeze this protocol and runner in GitHub before first execution.

Implementation clarification before acquiring 2025: ignore spaces in unit labels (`EUR / MWh` equals `EUR/MWh`). This was identified on the 2024 source bridge; no value conversion or strategy change.
