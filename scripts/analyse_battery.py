"""Run annual daily perfect-foresight benchmarks and December sensitivities."""
from pathlib import Path
from dataclasses import asdict
import sys,json,hashlib,platform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pandas as pd
import pyomo
import highspy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from zoneinfo import ZoneInfo
from market_flex.battery import Battery,optimise

def run():
    source=ROOT/'data/processed/fundamentals_prices_2024_hourly.csv'
    data=pd.read_csv(source);data['timestamp_utc']=pd.to_datetime(data.timestamp_utc,utc=True)
    expected=pd.date_range('2024-01-01','2025-01-01',freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
    out=ROOT/'reports';(out/'figures').mkdir(exist_ok=True)
    daily=[];dispatch=[];b=Battery()
    for zone in ['DE-LU','FR']:
        f=data[data.zone.eq(zone)].set_index('timestamp_utc').sort_index()
        assert f.index.equals(expected) and f.price_eur_mwh.notna().all()
        for date,g in f.groupby(f.index.tz_convert('Europe/Berlin').date):
            result=optimise(g.price_eur_mwh,b);result['zone']=zone;result['day_cet']=str(date);dispatch.append(result.reset_index())
            daily.append(dict(zone=zone,day_cet=str(date),hours=len(result),gross_margin_eur=result.gross_margin_eur.sum(),degradation_eur=result.degradation_eur.sum(),net_margin_eur=result.net_margin_eur.sum(),charge_mwh=result.charge_mw.sum(),discharge_mwh=result.discharge_mw.sum(),equivalent_full_cycles=result.discharge_mw.sum()/np.sqrt(b.round_trip_efficiency)/b.energy_mwh))
    daily=pd.DataFrame(daily);dispatch=pd.concat(dispatch,ignore_index=True)
    assert len(dispatch)==17568 and len(daily)==732
    daily.to_csv(out/'battery_daily_2024.csv',index=False)
    dispatch.to_csv(ROOT/'data/processed/battery_dispatch_2024.csv',index=False)
    summary=daily.groupby('zone').sum(numeric_only=True);summary.to_csv(out/'battery_summary_2024.csv')
    sensitivity=[]
    # Change one assumption at a time; compare net objectives within each scenario only.
    for label,scenario in [('efficiency_85pct',Battery(round_trip_efficiency=.85)),('degradation_0',Battery(degradation_eur_per_mwh_discharged=0)),('degradation_20',Battery(degradation_eur_per_mwh_discharged=20))]:
        for zone in ['DE-LU','FR']:
            f=data[data.zone.eq(zone)].set_index('timestamp_utc').sort_index();f=f[f.index.tz_convert('Europe/Berlin').month==12]
            net=gross=energy=0.
            for _,g in f.groupby(f.index.tz_convert('Europe/Berlin').date):
                r=optimise(g.price_eur_mwh,scenario);net+=r.net_margin_eur.sum();gross+=r.gross_margin_eur.sum();energy+=r.discharge_mw.sum()
            sensitivity.append(dict(scenario=label,zone=zone,**asdict(scenario),gross_margin_eur=gross,net_margin_eur=net,discharge_mwh=energy))
    for zone in ['DE-LU','FR']:
        f=daily[(daily.zone==zone)&daily.day_cet.str.startswith('2024-12')]
        sensitivity.append(dict(scenario='main',zone=zone,**asdict(b),gross_margin_eur=f.gross_margin_eur.sum(),net_margin_eur=f.net_margin_eur.sum(),discharge_mwh=f.discharge_mwh.sum()))
    sensitivity=pd.DataFrame(sensitivity);sensitivity.to_csv(out/'battery_december_sensitivity_2024.csv',index=False)
    sample=dispatch[dispatch.day_cet.eq('2024-12-12')];sample.to_csv(out/'battery_dispatch_2024-12-12.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'battery2024'})
    fig,axs=plt.subplots(3,1,figsize=(11,9),sharex=True)
    for zone,col in [('DE-LU','#215D9C'),('FR','#C96532')]:
        f=sample[sample.zone.eq(zone)];t=f.timestamp_utc.dt.tz_convert('Europe/Berlin')
        edges=pd.DatetimeIndex(t).append(pd.DatetimeIndex([t.iloc[-1]+pd.Timedelta(hours=1)]))
        axs[0].step(edges,list(f.price_eur_mwh)+[f.price_eur_mwh.iloc[-1]],where='post',label=zone,color=col)
        net=f.discharge_mw-f.charge_mw
        axs[1].step(edges,list(net)+[net.iloc[-1]],where='post',label=zone,color=col)
        ends=pd.DatetimeIndex(t).append(pd.DatetimeIndex([t.iloc[-1]+pd.Timedelta(hours=1)]))
        soc=list(f.soc_start_mwh)+[f.soc_end_mwh.iloc[-1]]
        axs[2].plot(ends,soc,label=zone,color=col)
    for ax,label in zip(axs,['Price (EUR/MWh)','Net export (MW)','Stored energy (MWh)']):
        ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(loc='upper left')
    axs[1].axhline(0,color='grey',lw=.6)
    axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=ZoneInfo('Europe/Berlin')))
    axs[2].set_xlabel('12 December 2024, CET (final 00:00 is 13 December)')
    fig.suptitle('Perfect foresight | Battery dispatch on the German peak-price day',weight='bold',fontsize=14)
    fig.text(.08,.01,'1 MW / 2 MWh; 90% round-trip efficiency; EUR 10/MWh discharged; daily start/end SOC = 1 MWh.',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.96))
    for ext in ['svg','png']:fig.savefig(out/f'figures/battery_peak_day_2024.{ext}',dpi=140,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    def table(df):
        return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f'{v:,.2f}' if isinstance(v,float) else str(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))
    report='''# Perfect-foresight BESS benchmark — 2024

## What we did and why

We optimised a separate 1 MW / 2 MWh battery in DE-LU and France for every local delivery day in 2024. The optimiser knows that day's actual prices. This creates an oracle benchmark: the best net operating margin within our daily constraints. Later, forecasts will replace those prices in the decision step; settlement will still use observed prices. The difference measures the financial cost of imperfect information under this experiment.

This is not demonstrated live trading income, a deployable forecast strategy, or a full battery investment valuation. It is not an unrestricted annual optimum: daily SOC restoration prevents inter-day arbitrage. For each day, a forecast-driven schedule under identical constraints cannot outperform the perfect-foresight objective except within solver tolerance.

## Assumptions and reasons

| Assumption | Choice and reason |
| --- | --- |
| Power / usable energy | 1 MW / 2 MWh: a simple two-hour asset |
| Efficiency | 90% round-trip, split symmetrically as sqrt(0.90) for charge and discharge |
| SOC | 0–2 MWh; each day starts and finishes at 1 MWh, avoiding a free terminal energy drawdown |
| Cycling cost | Illustrative EUR 10 per grid-side MWh discharged; not an empirically calibrated lifetime model |
| Timing | Hourly intervals, grouped by Europe/Berlin delivery date; DST days contain 23 or 25 hours |
| Operation | Binary mode prevents simultaneous charging and discharging, including at negative prices |
| Objective | Maximise sales minus purchases minus discharged-energy cycling cost |
| Trading | Price-taking, full acceptance, no market impact; each zone independent |
| Other costs | Fees assumed zero; capex, fixed O&M, taxes, grid tariffs, standby losses and auxiliary loads excluded |
| Other revenues | Intraday, balancing and ancillary services excluded |

## Mathematical model

For hourly charge c, discharge d and stored energy s:

- s[t+1] = s[t] + eta_charge*c[t] - d[t]/eta_discharge.
- 0 <= c[t] <= P*u[t]; 0 <= d[t] <= P*(1-u[t]); u is binary.
- 0 <= s[t] <= E; s[0] = s[T] = 0.5*E.
- Maximise sum(price[t]*(d[t]-c[t]) - cycling_cost*d[t]).

All intervals are one elapsed hour, so MW multiplied by one hour gives MWh. The implementation uses Pyomo and the HiGHS mixed-integer solver with a requested relative MIP gap of 1e-8. Every solve must terminate optimally. The same net objective is used to choose schedules and compare their outcomes.

## Annual results

'''+table(summary.reset_index().round(2))+'''

Currency columns are EUR for one battery. Energy columns are MWh. Equivalent full cycles use internal discharged energy divided by usable capacity: grid-side discharged MWh / discharge efficiency / 2 MWh. This counts energy throughput, not rainflow cycles or predicted degradation.

![Peak-day dispatch](figures/battery_peak_day_2024.svg)

Net export is positive when discharging and negative when charging. SOC is shown at interval boundaries. The future price spike is known to this benchmark; the chart must not be presented as successful spike prediction.

## December sensitivity: one assumption changed at a time

'''+table(sensitivity[['scenario','zone','gross_margin_eur','net_margin_eur','discharge_mwh']].round(2))+'''

These are re-optimised schedules, not simply revised accounting on the main schedule. Different scenarios have different objectives or constraints, so their net margins are not interchangeable oracle bounds. Zero cycling cost can admit multiple equally optimal dispatch schedules. At negative prices, sequential cycling can earn revenue partly by absorbing energy losses; simultaneous charging/discharging remains prohibited.

## Validation and reproducibility

All 732 daily problems were solved (366 per zone), covering 8,784 hours each. Each dispatch is checked for SOC bounds, power limits, energy balance, continuity, terminal SOC, mutual exclusivity and nonnegative daily net objective (idle is feasible). Analytical tests cover flat positive prices, a known two-hour arbitrage outcome, negative prices and both DST day lengths.

Source: the existing hourly dataset; only prices are used. The one missing French actual-fundamentals hour does not affect this model. The German Sequence 1 auction metadata limitation remains; see [price provenance](price_comparison_2024.md). Outputs are conditional on the selected price series.

```bash
python -m pip install -r requirements.txt
python scripts/analyse_fundamentals.py  # if processed data is absent
python scripts/analyse_battery.py
PYTHONPATH=src python -m unittest discover -s tests
```

Full dispatch is recreated in git-ignored `data/processed/battery_dispatch_2024.csv`. Published outputs: [daily margins](battery_daily_2024.csv), [annual summary](battery_summary_2024.csv), [December sensitivity](battery_december_sensitivity_2024.csv), [peak-day dispatch](battery_dispatch_2024-12-12.csv), and [run metadata](battery_validation_2024.json).

## What comes next and why

Use a simple historical price forecast to choose the same daily schedule before the declared auction cutoff. Settle that fixed schedule using actual prices and retain identical battery constraints. Compare MAE, extreme-event detection and net margin against this oracle. This makes Michael's forecast-to-financial-value question measurable, while the December case study provides Andreas's market context. Add ML only after the baseline and timestamp checks work.
'''
    (out/'battery_benchmark_2024.md').write_text(report)
    audit={'battery':asdict(b),'main_solves':732,'sensitivity_solves':186,'hours_per_zone':8784,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'python':platform.python_version(),'pyomo':pyomo.__version__,'highs':highspy.Highs().version(),'mip_rel_gap':1e-8,'all_dispatch_checks_passed':True}
    (out/'battery_validation_2024.json').write_text(json.dumps(audit,indent=2))
    print(summary.round(2).to_string());return summary
if __name__=='__main__':run()
