# Continuous-operation data

After a successful workflow run, this folder contains compressed CSVs:

- `dispatch_2025.csv.gz`: all interval forecasts, actual settlement prices, physical actions, SOC and financial accounting for each declared policy and oracle.
- `trade_ledger_2025.csv.gz`: committed day-ahead positions, decision cutoffs and signed cashflows for causal forecast strategies. The perfect-foresight benchmark is excluded from this trade ledger.

Download using GitHub's raw-file button and decompress with an archive tool. These repository copies persist after the downloadable workflow artifact expires. See [results](../../reports/continuous_results_2025.md) and [protocol](../../docs/continuous-operation-protocol.md).

Price inputs derive from Bundesnetzagentur | SMARD.de via Energy-Charts, CC BY 4.0. Source URLs and exact recovery fingerprints are in reports/dispatch_recovery_2025.json; this experiment records compressed-input fingerprints separately.
