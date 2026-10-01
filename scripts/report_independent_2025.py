"""Render the fixed holdout results; does not choose or tune a strategy."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def run():
    out=ROOT/'reports';m=pd.read_csv(out/'independent_metrics_2025.csv');d=pd.read_csv(out/'independent_daily_2025.csv');audit=json.loads((out/'independent_audit_2025.json').read_text());sel=json.loads((out/'ml_selection_2024.json').read_text())
    lines=['# Independent 2025 test: forecast accuracy versus battery margin','',
    '## What was frozen, and why','',
    'The protocol and executable were committed before acquiring 2025 prices: initial freeze `920694e82821c2c4d3de2556a3e22ef687dc9f8b`, with a unit-label whitespace correction from the 2024 source check in `2721a287f899fa93eed4334c728ae272669e94eb`. We tested the existing models rather than selecting new ones after seeing performance. The operational choice remains seven-day averaging in both zones. This is a previously uninspected historical holdout for this project, not a live trial.','',
    'Evaluation: 9 January–30 September 2025, 265 local delivery days / 6,359 hourly intervals per zone. January 1–8 provides historical inputs only. ML is reconstructed using the original January 9–August 30 2024 training data and fixed settings. Daily historical-price features update, but there is no refitting on 2025. Model ageing is therefore part of this transfer test.','',
    'The new API series exactly matched all 8,784 existing 2024 hourly prices in each zone (maximum difference zero). Both 2025 series passed exact hourly coverage, unique UTC timestamps, finite-price and EUR/MWh unit checks. The end date avoids the October 2025 quarter-hour product transition.','',
    '## Fixed experiment','',
    'A separate 1 MW / 2 MWh battery in each market, 90% round-trip efficiency, daily start/end SOC 50%, and EUR10/MWh discharged cycling cost. Price forecasts choose schedules before delivery; observed prices settle those unchanged schedules. Margins below are simulated operating margins after this cost, excluding fees, capex, financing, liquidity, imbalance settlement and operational failures. They are partial-period totals, not annual returns.','',
    '## Results','',
    '| Market | Fixed strategy | MAE (EUR/MWh) | Net margin (EUR) | Loss days | Gap to oracle (EUR) |','|---|---|---:|---:|---:|---:|']
    for r in m.itertuples():lines.append(f'| {r.zone} | {r.model} | {r.mae_eur_mwh:.2f} | {r.net_margin_eur:,.2f} | {r.loss_days} | {r.oracle_gap_eur:,.2f} |')
    lines+=['','![Forecast error and simulated margin](figures/independent_2025.svg)','','## What changed relative to the 2024 finding','']
    for z,g in m.groupby('zone'):
        base=g[g.model=='seven_day_same_hour'].iloc[0];rf=g[g.model==sel[z]['family_winners']['random_forest']].iloc[0];ridge=g[g.model==sel[z]['family_winners']['ridge']].iloc[0]
        lines.append(f'**{z}:** seven-day averaging earned EUR{base.net_margin_eur:,.2f}. The previously margin-selected Random Forest earned EUR{rf.net_margin_eur:,.2f} ({rf.net_margin_eur-base.net_margin_eur:+,.2f} versus the baseline), with MAE {rf.mae_eur_mwh:.2f} versus {base.mae_eur_mwh:.2f}. Ridge earned EUR{ridge.net_margin_eur:,.2f} ({ridge.net_margin_eur-base.net_margin_eur:+,.2f} versus the baseline).')
        lines.append('')
    lines+=['The table is a fixed-model comparison, not permission to reselect the operational strategy on this test. Lower MAE and better financial performance are distinct objectives; whether they align is an empirical result for each market and period. This one holdout cannot establish general superiority or statistical certainty.','',
    '## Losses and extremes','',
    '| Market | Strategy | Worst day (EUR) | Actual spike hours | Spike recall | Negative-price recall |','|---|---|---:|---:|---:|---:|']
    for r in m[m.model!='perfect_foresight'].itertuples():
        lines.append(f'| {r.zone} | {r.model} | {r.worst_day_eur:.2f} | {r.spike_actual_hours} | {r.spike_recall:.1%} | {r.negative_recall:.1%} |')
    lines+=['','A spike is a price above EUR200/MWh. Recall counts detected price events, not profitable battery actions. A battery can profit without predicting the exact spike level, and predicting an event does not guarantee the right SOC or profitable execution.','',
    '## How to use this in a job application','',
    '> Built and froze a chronological forecast-to-dispatch evaluation for DE-LU and French day-ahead markets, then tested fixed baseline, Ridge and Random Forest models on a previously uninspected 2025 period. Compared forecast error with simulated battery margin, losses and missed extremes under identical operating constraints.','',
    'This demonstrates timing-aware data engineering, optimisation, source verification and financial model evaluation. The next industry gap is execution realism: tradable bids, forecast publication vintages, continuous SOC, fees and imbalance exposure. A new extension should receive a new protocol and a new unseen test period rather than repeatedly tuning on this holdout.','',
    '## Reproduction and evidence','',
    '- Run `python scripts/evaluate_2025.py` and `python scripts/report_independent_2025.py`. Raw API JSON is cached locally; respect API rate limits on first acquisition. The 2024 source bridge can be acquired separately with `--bridge-only`.',
    '- [Frozen protocol](../docs/independent-2025-protocol.md), [source bridge](source_bridge_2024.json), [audit and source fingerprints](independent_audit_2025.json).',
    '- [Full metrics](independent_metrics_2025.csv), [daily results](independent_daily_2025.csv), [monthly margins](independent_monthly_2025.csv), [paired daily differences](independent_paired_daily_2025.csv).',
    '- Runtime gates check forecast history availability, unchanged settlement dispatch and oracle dominance on all scored days. Existing suite: 15 tests passed. Workflow executed as Python scripts.',
    '- Source: Bundesnetzagentur | SMARD.de via the [Energy-Charts API](https://api.energy-charts.info/), CC BY 4.0. Prices unmodified, transformed only into timezone-aware series for analysis. Exact requests, retrieval times, licenses and SHA256 hashes are recorded in the audit.',
    '- SDAC timing reference: [ENTSO-E Single Day-Ahead Coupling](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/).','']
    (out/'independent_results_2025.md').write_text('\n'.join(lines))
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    names={'latest_same_hour':'Latest hour','seven_day_same_hour':'Seven-day mean','ridge_alpha_0.1':'Ridge','ridge_alpha_10':'Ridge','rf_depth_6_leaf_5':'RF margin','rf_depth_6_leaf_20':'RF margin','rf_depth_12_leaf_20':'RF MAE','rf_depth_12_leaf_5':'RF MAE'}
    for ax,(z,g) in zip(axes,m[m.model!='perfect_foresight'].groupby('zone')):
        for r in g.itertuples():
            ax.scatter(r.mae_eur_mwh,r.net_margin_eur/1000,s=65,color='#157f79' if r.model=='seven_day_same_hour' else '#486a9a')
            ax.annotate(names[r.model],(r.mae_eur_mwh,r.net_margin_eur/1000),xytext=(5,5),textcoords='offset points',fontsize=8)
        ax.set_title(z);ax.set_xlabel('MAE (EUR/MWh); lower is better');ax.set_ylabel('Simulated net margin (thousand EUR)');ax.margins(.2);ax.grid(alpha=.2)
    fig.suptitle('Fixed-model transfer test • 9 Jan–30 Sep 2025')
    (out/'figures').mkdir(exist_ok=True);fig.savefig(out/'figures/independent_2025.svg');fig.savefig(out/'figures/independent_2025.png',dpi=150);plt.close(fig)
if __name__=='__main__':run()
