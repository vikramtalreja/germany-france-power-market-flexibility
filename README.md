# Germany–France Power Market Analytics & BESS Flexibility Model

A Python portfolio project connecting electricity market fundamentals with battery optimisation, developed by Vikram Talreja.

**Status: market analysis, forecasting, ML diagnosis and continuous battery operation completed.** See the [independent 2025 results](reports/independent_results_2025.md). Seven-day averaging retained the highest simulated margin among the tested forecast strategies in both markets, despite lower forecast error from some ML models. All results are simulated and subject to the documented market-execution limitations.

## Project direction

See [Forecast-Driven BESS Trading: project direction and experiment plan](docs/project-direction.md) for the combined Andreas/Michael/thesis rationale, MVP sequence, forecast-versus-settlement rules, evaluation metrics and future CV wording. Forecasting, battery and fixed-model robustness experiments are now complete; results and limitations are linked below.

## Questions

- How do day-ahead prices differ between Germany and France?
- How are high and negative prices associated with demand, wind, solar and residual load?
- What evidence helps explain selected high-price periods?
- How does battery dispatch value change with capacity, efficiency and cycling cost?
- How can network constraints affect zonal prices in an educational flow-based example?

## Implementation sequence

| Version | Main question | Status |
| --- | --- | --- |
| Day-ahead benchmark | What is achievable with perfect price knowledge? | Completed |
| Forecast-driven dispatch | Does forecast accuracy translate into financial value? | Completed, including ML diagnosis |
| Continuous operation | Does the result survive realistic interday SOC decisions? | Completed; retrospective comparison and sensitivities |
| Day-ahead + intraday | Can later information improve an existing position? | Engine and synthetic examples tested; historical data/execution validation pending |
| Energy + reserves | How should scarce battery capability be allocated? | Following extension |

Follow the [roadmap and completion criteria](docs/roadmap.md). The [Random Forest margin diagnosis](reports/ml_diagnosis_2025.md) is complete. [Continuous operation](reports/continuous_results_2025.md) is complete, with [interpretation](docs/continuous-operation-findings.md). The next step is verifying intraday data and specifying execution assumptions before implementing incremental trades. The intraday adjustment engine is implemented and tested with synthetic data; historical intraday strategy performance, FCR and aFRR are not demonstrated.

## Repository structure

| Path | Purpose |
| --- | --- |
| `notebooks/` | Price comparison notebook and two subsequent analysis outlines |
| `src/market_flex/` | Reusable Python functions as implementation progresses |
| `data/README.md` | Data schema and provenance requirements |
| `reports/` | Evidence-based market notes and exported figures |
| `docs/roadmap.md` | Milestones and completion criteria |
| `requirements.txt` | Initial analysis and optimisation dependencies |

## Local setup

Requires Python 3.11 or later.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
jupyter lab
```

Dependencies are a starting list, not a tested or locked environment. Notebook 01 requires the five source CSV exports listed in `scripts/analyse_fundamentals.py` in `data/raw/`; notebook 02 reproduces the December case study; notebook 03 reproduces the battery benchmark. Run `python scripts/analyse_prices.py` to reproduce the price summary and chart.

## Analytical conventions

- Store timezone-aware timestamps in UTC and preserve the source delivery resolution and interval duration. Use local time only for explicitly labelled displays.
- Treat the German market series as the DE-LU bidding zone, labelled consistently alongside France.
- Define residual load here as demand minus wind minus solar; this is not total demand net of every low-marginal-cost source.
- Define the spread as DE-LU price minus France price, in EUR/MWh.
- High prices alone do not establish physical scarcity. Price correlations alone do not establish causation.
- Start with perfect-foresight, price-taking battery arbitrage as a benchmark. Revenue is not realised trading profit: document fees, degradation, forecast errors and other exclusions.
- Model batteries separately by bidding zone. A price spread does not imply a battery can freely trade across borders.

## Data and reproducibility

Candidate sources to assess include ENTSO-E Transparency Platform, SMARD and RTE. The first comparison uses two user-supplied ENTSO-E GUI price exports; provenance and fingerprints are in the result report. Verify coverage, access conditions, licences and redistribution rights before adding datasets. Record retrieval dates, units, missing intervals and aggregation rules. Never commit API keys or confidential thesis/employer material.

## Immediate milestone

Verify one market’s intraday data and execution assumptions, then extend the preserved day-ahead ledger with incremental intraday trades. Continuous SOC and ML diagnosis are complete. See the [current roadmap](docs/roadmap.md); completed market and forecasting results remain linked below.

## Background

This independent portfolio project builds on my MSc thesis experience at Fraunhofer ISE in EV/PV/BESS optimisation under uncertainty. It does not include Fraunhofer source code or data and does not imply institutional endorsement.

## Run the fundamentals analysis

```bash
python scripts/analyse_fundamentals.py
# Optional: specify a directory containing the five original exports
python scripts/analyse_fundamentals.py /path/to/exports
# Focused data-handling tests (macOS/Linux)
PYTHONPATH=src python -m unittest discover -s tests
```

The script writes the UTC hourly dataset into git-ignored `data/processed/` and aggregate tables, selected event records, validation notes and a chart into `reports/`. Missing actual observations are not imputed.

## Reproduce the December case study

After creating the processed fundamentals dataset, run `python scripts/analyse_december.py` or open `notebooks/02_high_price_cases.ipynb`. This produces the event chart, December top-20 hours per zone, hourly/daily spreads and the analyst report. Results are retrospective; causal attribution remains incomplete. Battery optimisation is implemented in the subsequent stages below.

## Battery benchmark: what and why

Run `python scripts/analyse_battery.py` after the fundamentals pipeline. A Pyomo/HiGHS MILP optimises separate 1 MW / 2 MWh batteries for each 2024 delivery day. Perfect foresight establishes a daily oracle for later forecast comparisons; it is not demonstrated trading income. See [the formulation, assumptions, results and next step](reports/battery_benchmark_2024.md) and [development notes](docs/development-notes.md). Seven focused tests pass; the notebook wrapper is syntax-checked, while the complete workflow was executed as a Python script.

## Forecast baselines: accuracy versus financial outcomes

Run `python scripts/analyse_forecasts.py` to compare latest-same-hour and seven-day-mean price forecasts with the daily oracle on 9 January–31 December 2024. Forecasts choose fixed schedules; actual prices determine settlement, including losses. See [results and timing assumptions](reports/forecast_baselines_2024.md), `notebooks/04_forecast_baselines.ipynb`, and the ongoing [development notes](docs/development-notes.md). Eleven tests pass; notebook syntax is checked, with execution validated through the Python script.

## Diagnose forecast decisions before ML

Run `python scripts/analyse_failures.py` after the forecast workflow. See [why the seven-day strategy earned more and where it failed](reports/forecast_failures_2024.md), including exact margin reconciliation, selected loss-day schedules and missed-extreme actions. The analysis diagnoses existing decisions without tuning forecasts or deleting losses. Notebook: `notebooks/05_forecast_failures.ipynb`.

## ML evaluation protocol — specified before training

The [ML protocol](docs/ml-evaluation-protocol.md) and [configuration](config/ml-evaluation.json) fix chronological dates, available features, model candidates and financial selection rules. September–December 2024 is labelled retrospective because we already inspected that year. The protocol has now been executed; see [ML results](reports/ml_results_2024.md).

## ML results — chronological retrospective comparison completed

Run `python scripts/analyse_ml.py` to fit the declared Ridge and Random Forest candidates, select on July–August validation and evaluate on September–December. The seven-day baseline won validation margin in both zones and retained the highest evaluation margin among the tested forecast strategies. Random Forest improved MAE but reduced simulated margin relative to that baseline. See [results, assumptions and reproducibility](reports/ml_results_2024.md) and `notebooks/06_ml_evaluation.ipynb`. Fifteen tests pass; the full workflow ran as a script and notebook syntax was checked.


## Independent 2025 robustness test — completed

The [test protocol](docs/independent-2025-protocol.md) and runner were frozen before 2025 prices were acquired. The new source exactly reproduced all 2024 project prices, then supplied a previously uninspected 9 January–30 September 2025 period. Existing candidates and January–August 2024 training stayed fixed. See the [report and chart](reports/independent_results_2025.md) for margins, forecast errors, losses, provenance and portfolio wording. Run `python scripts/evaluate_2025.py` followed by `python scripts/report_independent_2025.py`.

## ML diagnosis — completed

See the [diagnosis and interview explanation](reports/ml_diagnosis_2025.md) and [all 16 hourly cases and charts](reports/ml_diagnosis_hourly_2025.md). The analysis reconciles sales revenue, purchase expenditure and cycling cost and shows both missed opportunities and RF wins. Recovery passed all published daily-result checks; the full reconstructed hourly CSV is saved under data/recovered.

## Recover hourly data without a local installation

The **Recover dispatch and diagnose ML** GitHub Actions workflow reconstructs the frozen experiment, checks every daily financial result and saves permanent compressed CSV files under [data/recovered](data/recovered/README.md). It also provides an uncompressed CSV in a downloadable workflow artifact. The first recovery run succeeded; see [run status](reports/recovery-status.json) and [data download instructions](data/recovered/README.md). No user upload is required.

## Continuous operation: why daily boundaries matter

The battery now carries physical SOC between days and projects tomorrow's opening state through existing commitments. It plans two delivery days but commits only the first. Under the unchanged seven-day forecast, simulated zero-fee margin increased from EUR55,361.95 to EUR59,810.90 in DE-LU and from EUR33,633.12 to EUR40,068.58 in France over 9 January–30 September 2025. Initial and final energy are matched. This is retrospective evidence, not a new unseen test or demonstrated trading income.

Lower purchase expenditure and cycling explain most of the improvement; the battery usually ends empty rather than storing energy overnight. Read the [results](reports/continuous_results_2025.md), [interpretation and interview explanation](docs/continuous-operation-findings.md), [frozen protocol](docs/continuous-operation-protocol.md) and [audit](reports/continuous_audit_2025.json). All 20 tests and full-run accounting/physical checks passed. Full dispatch and the separate trade ledger are retained in [data/continuous](data/continuous/README.md).

Reproduce with `python scripts/analyse_continuous.py` using the recovered inputs and versions recorded in the audit, or run the **Continuous battery operation** GitHub Actions workflow. Historical results remain day-ahead only. The new intraday engine has synthetic validation; historical intraday evaluation and reserve strategies remain future work.

## Intraday extension and printable learning guide

[Intraday data and execution verification](docs/intraday-data-and-execution.md) distinguishes IDA1 auctions from ID1 indices and records the historical-data gap. The new engine preserves original day-ahead positions/cashflows, adds signed intraday adjustments, enforces physical feasibility and volume limits, and settles actual ID prices only after planning. All 28 tests pass locally. [Synthetic worked examples](reports/intraday_synthetic_demo.md) show beneficial and losing adjustments; these are not historical profitability results.

Run `python scripts/demo_intraday.py` or the **Intraday accounting tests** GitHub Actions workflow. Historical DE-LU IDA1 evaluation awaits a verified usable dataset, publication information and execution specification. No actual intraday prices have been invented or replaced with day-ahead data.

Read the [complete learning and presentation guide](docs/project-learning-guide.md): beginner market concepts, battery equations, forecast evaluation, findings, intraday ledger examples, glossary and a five-minute presentation script. Printable Word/PDF versions are delivered separately; this Markdown source stays with the project.

## Printable master guide

Open [docs/printable](docs/printable/README.md) and download **Power_Market_BESS_Project_Guide.pdf**. The guide explains the whole project, historical findings, concepts, synthetic intraday accounting and the plan for auction data. Current revision: 21 October 2026, revision 3.
