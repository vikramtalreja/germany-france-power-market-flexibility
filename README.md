# Germany–France Power Market Analytics & BESS Flexibility Model

A Python portfolio project connecting electricity market fundamentals with battery optimisation, developed by Vikram Talreja.

**Status: 2024 prices, actual fundamentals and December case study completed.** See the [December price-spike case study](reports/december_case_2024.md). See [fundamentals results and data-quality notes](reports/fundamentals_2024.md) and the [initial price comparison](reports/price_comparison_2024.md). France has one missing hour of actuals, retained as missing. The [perfect-foresight battery benchmark](reports/battery_benchmark_2024.md) is now implemented; forecast-driven dispatch remains planned.

## Project direction

See [Forecast-Driven BESS Trading: project direction and experiment plan](docs/project-direction.md) for the combined Andreas/Michael/thesis rationale, MVP sequence, forecast-versus-settlement rules, evaluation metrics and future CV wording. Forecasting and battery experiments are planned; completed results are linked above.

## Questions

- How do day-ahead prices differ between Germany and France?
- How are high and negative prices associated with demand, wind, solar and residual load?
- What evidence helps explain selected high-price periods?
- How does battery dispatch value change with capacity, efficiency and cycling cost?
- How can network constraints affect zonal prices in an educational flow-based example?

## Planned workflow

1. **Market fundamentals:** load and validate prices, demand, wind and solar; calculate residual load and DE–FR spreads.
2. **High-price case studies:** investigate selected periods, documenting supporting evidence and alternative explanations.
3. **BESS optimisation:** use Pyomo to model power, energy, efficiency, state of charge, terminal energy and mutually exclusive charging/discharging.
4. **Network extension:** build a small illustrative PTDF/RAM constraint model. This will not reproduce operational European flow-based market coupling.

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

## First milestone

Obtain a documented, common historical period of DE-LU and French day-ahead prices, validate timestamps and units, and produce one comparison chart with a short market note. Add demand and generation after the price pipeline works.

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

After creating the processed fundamentals dataset, run `python scripts/analyse_december.py` or open `notebooks/02_high_price_cases.ipynb`. This produces the event chart, December top-20 hours per zone, hourly/daily spreads and the analyst report. Results are retrospective; causal attribution and battery optimisation remain future work.

## Battery benchmark: what and why

Run `python scripts/analyse_battery.py` after the fundamentals pipeline. A Pyomo/HiGHS MILP optimises separate 1 MW / 2 MWh batteries for each 2024 delivery day. Perfect foresight establishes a daily oracle for later forecast comparisons; it is not demonstrated trading income. See [the formulation, assumptions, results and next step](reports/battery_benchmark_2024.md) and [development notes](docs/development-notes.md). Seven focused tests pass; the notebook wrapper is syntax-checked, while the complete workflow was executed as a Python script.
