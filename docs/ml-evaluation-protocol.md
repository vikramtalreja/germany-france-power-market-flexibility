# ML evaluation protocol — version 1

Recorded 1 October 2026. **Specified, not trained.** Configuration: [ml-evaluation.json](../config/ml-evaluation.json).

## What we are doing and why

Test whether a small machine-learning model improves battery decisions over the two historical baselines. Define dates, information rules, candidates and success criteria before fitting. We will report financial margin alongside prediction error, rather than assume that complexity or lower MAE guarantees better decisions.

We have already inspected 2024, including loss days and extremes. The final 2024 window is therefore a **retrospective chronological evaluation**, not an untouched holdout.

## Chronological stages

Dates are local delivery dates in Europe/Berlin.

| Stage | Target dates | Use |
| --- | --- | --- |
| Initial training | 9 January–29 June 2024 | Fit candidates and preprocessing |
| Validation | 1 July–30 August 2024 | Select parameters and strategy |
| Final training | 9 January–30 August 2024 | Refit selected candidates once |
| Evaluation | 1 September–31 December 2024 | Evaluate frozen models against baselines and oracle |

The first eight January days provide feature history. June 30 is excluded from initial training and August 31 from selection/final training: these are D-1 at the first validation/evaluation cutoffs and violate our conservative completed-day policy.

No random split and no refitting inside validation or evaluation. Lag features still update each day from eligible observed prices; this is distinct from updating learned model parameters. Fit models separately by zone.

## Information timing and feature construction

For delivery day D, the chosen experimental cutoff is D-1 at 09:00 local time. This is a modelling choice, not a verified exchange gate-closure rule. Use complete historical delivery days D-8 through D-2 only. Availability and revision history of the historical exports remain assumptions.

For every historical training row, reconstruct features at that row's own cutoff. Features:

- Target local hour: sine/cosine of 2*pi*hour/24.
- Target weekday: seven fixed one-hot columns, Monday through Sunday.
- Latest available same-hour historical price.
- Seven-day same-hour mean, population standard deviation, minimum and maximum.
- Mean of seven daily mean prices.

Average a repeated historical autumn hour within its day before computing same-hour statistics; each historical day receives equal weight. Omit the nonexistent spring hour. Latest same hour falls back to the previous available day within the seven-day window. Repeated target autumn hours receive identical features. Each daily mean includes all that day's elapsed hourly intervals. Reject unexplained missing history rather than filling from future observations.

No target-day actual demand, wind, solar, residual load, prices or spreads. No D-1 prices without a separately documented publication-time policy. This first ML experiment forecasts from calendar and historical prices only.

Fit numeric scaling for Ridge on its training rows only; leave weekday indicators unscaled. Do not learn transformations using validation/evaluation rows. Random Forest uses unscaled features.

## Candidate set and selection

Use scikit-learn; record exact package versions at execution.

- Ridge alpha: 0.1, 1, 10, 100, in that order.
- Random Forest: 200 trees; max depth 6 or 12; minimum leaf size 5 or 20. Enumerate depth first, then leaf size in ascending order. Max features 1.0, seed 42, one worker.
- Retain latest-same-hour and seven-day-mean baselines.

No extra search, ensembles, output clipping, loss-day filters or spike overrides in version 1. Negative forecasts remain possible.

For each zone, rank candidates by total validation net battery margin. Form a near-tie set of candidates within EUR 1 of the highest margin; select the lowest hourly MAE within that set. Exact remaining ties use the configuration order: latest baseline, seven-day baseline, Ridge, Random Forest. A baseline may win.

Separately record the validation MAE winner as a secondary diagnostic. This comparison is declared now, rather than chosen after evaluation.

Select one Ridge and one Random Forest using the same rule within each family; refit them once on final training data. Evaluate both family winners, both baselines and perfect foresight on the common September–December window, clearly identifying the operationally selected strategy. Also evaluate the frozen validation MAE winner if it is a different candidate. Do not retune or change the operational winner using evaluation results.

## Financial experiment stays fixed

Use the existing 1 MW / 2 MWh model, 90% round-trip efficiency, daily starting/terminal SOC 50%, EUR 10 per discharged MWh cycling cost and mutually exclusive charge/discharge.

Forecast prices choose the schedule. Actual prices settle its unchanged quantities. Keep losing days. Recompute the oracle on identical dates; do not compare partial-period ML margins to full-year benchmark totals.

The price-taking/full-acceptance assumptions and exclusions of fees, capex, grid tariffs, other operating costs and other markets remain. No live trading profitability is claimed.

## Required results and checks

Report hourly MAE/RMSE; spike (> EUR 200/MWh) and negative-price (< 0) precision/recall and event counts; gross margin, cycling cost, net margin, oracle gap, loss-day count, worst day, monthly results and discharged energy. Include paired daily margin differences versus the seven-day baseline.

Record training boundaries, parameters, features, seed, source hashes, installed versions and data exclusions. Report failures and baseline wins.

Before accepting results, verify:

1. Changing future observations leaves earlier features and predictions unchanged.
2. Every training target and feature obeys its cutoff; preprocessing fits only training data.
3. Each target interval appears once per zone/model, including 23/25-hour DST days.
4. Physical dispatch constraints hold and settlement does not change quantities.
5. Actual daily net margin does not exceed the same-day oracle beyond solver tolerance.

The primary question is whether the validation-selected strategy improves evaluation net margin over the seven-day baseline. A single, previously inspected year does not establish generalisation or statistical significance.

## Independent follow-up

Proposed uninspected period: 9 January–30 September 2025, subject to source/product/resolution verification. It has not been acquired or validated for this project.

Freeze the code and selection procedure before inspecting strategy performance there. Verify that products and interval durations are comparable. Do not silently aggregate a different traded product and call it the same experiment. If the proposed dataset is unsuitable, record the revised protocol before reviewing its performance.

## Next action

Implement the feature builder and small candidate set, then execute this protocol. Update development notes with what was implemented, why, validation results and any deviation. No ML model has been fitted as part of this protocol step.
