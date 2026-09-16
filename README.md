# Germany–France Power Market Analytics & BESS Flexibility Model

A Python portfolio project connecting electricity market fundamentals with battery optimisation, developed by Vikram Talreja.

**Status: repository scaffold.** Data collection, analysis and optimisation are planned; no empirical findings or model results are claimed yet.

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
| `notebooks/` | Three analysis notebooks, initially outlines |
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

Dependencies are a starting list, not a tested or locked environment. The notebooks contain outlines only and do not require data yet.

## Analytical conventions

- Store timezone-aware timestamps in UTC and preserve the source delivery resolution and interval duration. Use local time only for explicitly labelled displays.
- Treat the German market series as the DE-LU bidding zone, labelled consistently alongside France.
- Define residual load here as demand minus wind minus solar; this is not total demand net of every low-marginal-cost source.
- Define the spread as DE-LU price minus France price, in EUR/MWh.
- High prices alone do not establish physical scarcity. Price correlations alone do not establish causation.
- Start with perfect-foresight, price-taking battery arbitrage as a benchmark. Revenue is not realised trading profit: document fees, degradation, forecast errors and other exclusions.
- Model batteries separately by bidding zone. A price spread does not imply a battery can freely trade across borders.

## Data and reproducibility

Candidate sources to assess include ENTSO-E Transparency Platform, SMARD and RTE. No data has been downloaded. Verify coverage, access conditions, licences and redistribution rights before adding datasets. Record retrieval dates, units, missing intervals and aggregation rules. Never commit API keys or confidential thesis/employer material.

## First milestone

Obtain a documented, common historical period of DE-LU and French day-ahead prices, validate timestamps and units, and produce one comparison chart with a short market note. Add demand and generation after the price pipeline works.

## Background

This independent portfolio project builds on my MSc thesis experience at Fraunhofer ISE in EV/PV/BESS optimisation under uncertainty. It does not include Fraunhofer source code or data and does not imply institutional endorsement.
