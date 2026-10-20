# Recoverable inputs and hourly outputs

The GitHub Actions recovery job is intended to save:

- `independent_dispatch_2025.csv.gz`: the full reconstructed hourly CSV, compressed for storage. Download with GitHub's **Raw / Download raw file**, then unzip using an archive utility.
- `prices_DE-LU_2024.csv.gz`, `prices_FR_2024.csv.gz` and corresponding 2025 files: public price inputs.

Files appear only after a successful run. The uncompressed CSV is also in the workflow's downloadable artifact (90-day retention); the repository copies remain after that expires.

Price source: Bundesnetzagentur | SMARD.de via Energy-Charts API, CC BY 4.0. Price values are unchanged; timestamps are represented in UTC and data reformatted. Exact URLs and fingerprints are in `reports/independent_audit_2025.json`; recovery checks are in `reports/dispatch_recovery_2025.json` when successful.

Recovery reconstructs models using frozen 2024 price-only training. It checks API response hashes against the original retrievals and all daily financial totals against published results. The original hourly file had no retained fingerprint; a successful recovery establishes agreement of aggregate results, not byte-identical hourly schedules where solver ties exist. Hourly diagnoses refer to reconstructed schedules.
