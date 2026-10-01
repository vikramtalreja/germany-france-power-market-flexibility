"""Generate the ML report from saved experiment results, without retuning."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def table(df):
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f'{x:,.2f}' if isinstance(x,float) else str(x) for x in row)+' |' for row in df.itertuples(index=False,name=None))
def write_report(metrics,daily,selections):
    out=ROOT/'reports';ev=metrics[metrics.stage=='evaluation'].copy();val=metrics[metrics.stage=='validation']
    findings=[]
    for zone,s in selections.items():
        z=ev[ev.zone==zone].set_index('model');selected=z.loc[s['operational']];base=z.loc['seven_day_same_hour'];accuracy=z.loc[s['mae_winner']]
        findings.append(f"- **{zone}:** validation selected **{s['operational']}** for financial performance. Its evaluation net margin was **EUR {selected.net_margin_eur:,.2f}**, a difference of **EUR {selected.net_margin_eur-base.net_margin_eur:,.2f}** versus the seven-day baseline. The validation MAE winner was **{s['mae_winner']}**; its evaluation MAE was **{accuracy.mae_eur_mwh:.2f} EUR/MWh** and net margin **EUR {accuracy.net_margin_eur:,.2f}**.")
        rf=z.loc[s['family_winners']['random_forest']]
        findings.append(f"- {zone}: the margin-selected Random Forest had MAE **{rf.mae_eur_mwh:.2f}** versus the seven-day baseline's **{base.mae_eur_mwh:.2f} EUR/MWh**, but net margin was **EUR {rf.net_margin_eur:,.2f}** versus **EUR {base.net_margin_eur:,.2f}**. Lower average price error did not translate into higher battery margin in this comparison. This does not isolate which prediction errors caused the difference.")
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'ml2024'})
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True)
    for ax,zone in zip(axes,['DE-LU','FR']):
        names=list(dict.fromkeys(['seven_day_same_hour',selections[zone]['operational'],selections[zone]['mae_winner'],'perfect_foresight']))
        for name in names:
            d=daily[(daily.zone==zone)&(daily.stage=='evaluation')&(daily.model==name)].sort_values('day_cet')
            ax.plot(pd.to_datetime(d.day_cet),d.net_margin_eur.cumsum()/1000,label=name)
        ax.set_title(zone,loc='left',weight='bold');ax.grid(alpha=.2);ax.tick_params(axis='x',rotation=35);ax.legend(fontsize=7)
    axes[0].set_ylabel('Cumulative simulated net margin (EUR thousands)')
    fig.suptitle('Chronological ML evaluation | Choices frozen after validation',weight='bold',fontsize=14)
    fig.text(.05,.012,'September–December 2024; retrospective, previously inspected period. Cycling cost included; other costs excluded.',fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.95))
    for ext in ['svg','png']:fig.savefig(out/f'figures/ml_evaluation_2024.{ext}',dpi=140,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    report='''# ML price forecasts evaluated through battery decisions

## What we did and why

Implemented the [predeclared protocol](../docs/ml-evaluation-protocol.md): four Ridge settings and four Random Forest settings per zone, compared with both historical baselines. Models use only calendar and eligible historical prices. We selected candidates by validation battery margin, separately tracked the validation MAE winner, then evaluated without retuning.

Initial fitting used 9 January–29 June. Validation used 1 July–30 August. Final fitting used targets through 30 August; frozen models were evaluated from 1 September through 31 December. Feature history updates daily, but learned parameters do not. Model choices for both zones were saved before evaluation began.

**This is a retrospective chronological evaluation, not an untouched holdout:** the project had already inspected 2024. No 2025 data have been used. These results do not establish live profitability or generalisation.

## What happened to the validation choices?

'''+ '\n'.join(findings)+'''

## Evaluation results: identical 122 days / 2,929 hours per model and zone

'''+table(ev[['zone','model','mae_eur_mwh','rmse_eur_mwh','net_margin_eur','oracle_gap_eur','loss_days','worst_day_eur']].round(2))+'''

Margins are EUR for one simulated 1 MW / 2 MWh battery, after EUR 10/MWh discharged cycling cost and before other costs. Each day starts/ends at 50% SOC with 90% round-trip efficiency. Oracle MAE/RMSE are zero by construction, not predictive achievements. Compare these totals only within this evaluation period, not with earlier annual totals.

![Evaluation margins](figures/ml_evaluation_2024.svg)

The operational choice remains the validation-selected strategy even if another candidate earns more in evaluation. Both family winners are shown, and an additional MAE winner is shown if different. These are reported comparisons, not permission to retrospectively replace the selected strategy.

## Validation: the evidence used to select candidates

'''+table(val[['zone','model','mae_eur_mwh','net_margin_eur']].round(2))+'''

The highest validation net margin defines a near-tie set within EUR 1. Lower MAE breaks that tie; remaining ties follow the declared order. Baselines are eligible. Hyperparameters were not searched further after seeing evaluation results.

## Extreme-event diagnostics

'''+table(ev[ev.model!='perfect_foresight'][['zone','model','spike_actual_hours','spike_predicted_hours','spike_precision','spike_recall','negative_actual_hours','negative_predicted_hours','negative_precision','negative_recall']].round(3))+'''

Spikes are strictly above EUR 200/MWh; negatives strictly below zero. Precision/recall are fractions; undefined ratios remain missing. Event classification is distinct from battery action and whole-day margin. The earlier loss analysis explains why missed threshold crossings need not prevent profitable discharge.

## Implementation and validation

Features are target hour sine/cosine, weekday indicators, latest same-hour price, seven-day same-hour mean/std/min/max, and mean of seven daily mean prices. History is D-8 through D-2, with a D-1 09:00 local experimental decision cutoff. Every training row reconstructs its own historical information set. Ridge scales numeric columns using training statistics only; weekday indicators remain unscaled. Random Forest uses unscaled inputs, 200 trees and seed 42.

The JSON configuration stores max_features as 1; implementation explicitly casts to float 1.0, preserving the protocol's all-features setting rather than sklearn's integer-one-feature meaning. This is a type clarification, not a post-result hyperparameter change.

Checks cover source continuity, eligible training targets, future-data perturbation, frozen preprocessing/predictions, DST hours, near-tie selection, physical feasibility, unchanged dispatch at settlement and same-day oracle dominance. No future actual fundamentals were used. The notebook wrapper is syntax-checked; end-to-end execution was through the Python script, not a Jupyter kernel.

Important remaining limits: historical price publication vintages are unverified; German Sequence 1 product metadata is still pending; quantities are assumed fully accepted; fees, grid tariffs, capex and other operating costs are excluded; daily SOC reset prevents inter-day arbitrage. Features have no weather, forward fundamentals or cross-market information. A short seasonal validation window and a frozen model may not transfer well to autumn/winter; the present comparison does not isolate the cause of any performance change.

## Reproduction and outputs

```bash
python -m pip install -r requirements.txt
python scripts/analyse_fundamentals.py  # if processed data is absent
python scripts/analyse_ml.py
PYTHONPATH=src python -m unittest discover -s tests
```

- [Frozen selections](ml_selection_2024.json)
- [All metrics](ml_metrics_2024.csv)
- [Daily results](ml_daily_2024.csv) and [monthly results](ml_monthly_2024.csv)
- [Paired daily differences versus seven-day baseline](ml_paired_daily_2024.csv)
- [Training-boundary audit](ml_fit_audit_2024.csv)
- [Versions, hashes, parameters and checks](ml_validation_2024.json)

Full hourly schedules and feature-time audit are recreated in git-ignored data/processed/ml_dispatch_2024.csv and ml_feature_timing_2024.csv.

## Next step

Review whether validation-selected accuracy and financial advantages persisted, without retuning on this evaluation period. Freeze this run as a benchmark. Any new features, rolling refits or alternative objective require a separately versioned experiment and genuinely uninspected data for stronger evidence. Do not present an ML result as an upgrade merely because it is more complex.
'''
    (out/'ml_results_2024.md').write_text(report)
