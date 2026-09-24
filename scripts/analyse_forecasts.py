"""Historical price forecasts -> fixed battery schedules -> actual settlement."""
from pathlib import Path
from dataclasses import asdict
from datetime import timedelta
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from market_flex.battery import Battery,optimise
from market_flex.forecast import forecast,settle,MODELS

def event_scores(actual,pred,threshold):
    a=actual>threshold if threshold else actual<0
    p=pred>threshold if threshold else pred<0
    tp=int((a&p).sum()); return (tp/int(p.sum()) if p.sum() else np.nan,tp/int(a.sum()) if a.sum() else np.nan,int(a.sum()),int(p.sum()))

def run():
    source=ROOT/'data/processed/fundamentals_prices_2024_hourly.csv'
    data=pd.read_csv(source);data.timestamp_utc=pd.to_datetime(data.timestamp_utc,utc=True)
    out=ROOT/'reports';battery=Battery();daily=[];hourly=[];timing=[]
    expected=pd.date_range('2024-01-01','2025-01-01',freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
    for zone in ['DE-LU','FR']:
        prices=data[data.zone.eq(zone)].set_index('timestamp_utc').price_eur_mwh.sort_index()
        assert prices.index.equals(expected) and np.isfinite(prices).all()
        for day,actual in prices.groupby(prices.index.tz_convert('Europe/Berlin').date):
            if day<pd.Timestamp('2024-01-09').date():continue
            oracle=optimise(actual,battery);oracle_net=oracle.net_margin_eur.sum()
            for model in (*MODELS,'perfect_foresight'):
                if model=='perfect_foresight':pred=actual;schedule=oracle
                else:
                    pred,audit=forecast(prices,actual.index,model)
                    timing.append(dict(zone=zone,model=model,day_cet=str(day),**audit))
                    schedule=optimise(pred,battery)
                settled=settle(schedule,actual)
                assert oracle_net-settled.net_margin_eur.sum()>=-1e-5
                for field in ['charge_mw','discharge_mw','soc_start_mwh','soc_end_mwh']:
                    assert settled[field].equals(schedule[field])
                settled['zone']=zone;settled['model']=model;settled['day_cet']=str(day);hourly.append(settled.reset_index())
                daily.append(dict(zone=zone,model=model,day_cet=str(day),hours=len(actual),gross_margin_eur=settled.gross_margin_eur.sum(),degradation_eur=settled.degradation_eur.sum(),net_margin_eur=settled.net_margin_eur.sum(),oracle_gap_eur=oracle_net-settled.net_margin_eur.sum(),mae_eur_mwh=(pred-actual).abs().mean()))
        print(zone+' complete',flush=True)
    daily=pd.DataFrame(daily);hourly=pd.concat(hourly,ignore_index=True);timing=pd.DataFrame(timing)
    assert len(daily)==358*2*3 and len(hourly)==8592*2*3
    results=[]
    for (zone,model),h in hourly.groupby(['zone','model']):
        d=daily[(daily.zone==zone)&(daily.model==model)]
        sp,sr,sa,sn=event_scores(h.actual_eur_mwh,h.forecast_eur_mwh,200)
        np_,nr,na,nn=event_scores(h.actual_eur_mwh,h.forecast_eur_mwh,0)
        results.append(dict(zone=zone,model=model,hours=len(h),days=len(d),mae_eur_mwh=(h.actual_eur_mwh-h.forecast_eur_mwh).abs().mean(),spike_precision=sp,spike_recall=sr,actual_spike_hours=sa,predicted_spike_hours=sn,negative_precision=np_,negative_recall=nr,actual_negative_hours=na,predicted_negative_hours=nn,gross_margin_eur=d.gross_margin_eur.sum(),degradation_eur=d.degradation_eur.sum(),net_margin_eur=d.net_margin_eur.sum(),oracle_gap_eur=d.oracle_gap_eur.sum(),worst_day_eur=d.net_margin_eur.min(),loss_days=int((d.net_margin_eur<-1e-6).sum())))
    summary=pd.DataFrame(results);summary.to_csv(out/'forecast_summary_2024.csv',index=False)
    daily.to_csv(out/'forecast_daily_2024.csv',index=False)
    hourly.to_csv(ROOT/'data/processed/forecast_dispatch_2024.csv',index=False)
    timing.to_csv(ROOT/'data/processed/forecast_timing_2024.csv',index=False)
    hourly[hourly.day_cet.eq('2024-12-12')].to_csv(out/'forecast_dispatch_2024-12-12.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'forecast2024'})
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True)
    labels={'latest_same_hour':'Latest same hour','seven_day_same_hour':'Seven-day mean','perfect_foresight':'Perfect foresight'}
    colors={'latest_same_hour':'#215D9C','seven_day_same_hour':'#C96532','perfect_foresight':'#555555'}
    for ax,zone in zip(axes,['DE-LU','FR']):
        for m in (*MODELS,'perfect_foresight'):
            d=daily[(daily.zone==zone)&(daily.model==m)].sort_values('day_cet')
            ax.plot(pd.to_datetime(d.day_cet),d.net_margin_eur.cumsum()/1000,label=labels[m],color=colors[m])
        ax.set_title(zone,loc='left',weight='bold');ax.grid(alpha=.2);ax.legend(fontsize=8);ax.tick_params(axis='x',rotation=30)
    axes[0].set_ylabel('Cumulative simulated net margin (EUR thousands)')
    fig.suptitle('Forecast-driven battery schedules | Financial outcomes',weight='bold',fontsize=15)
    fig.text(.06,.015,'9 Jan–31 Dec 2024; identical daily battery constraints. Cycling cost included; other costs excluded.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.96))
    for ext in ['svg','png']:fig.savefig(out/f'figures/forecast_margins_2024.{ext}',dpi=140,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    def table(df):
        return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f'{v:,.2f}' if isinstance(v,float) else str(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))
    findings=[]
    for z in ['DE-LU','FR']:
        s=summary[(summary.zone==z)&summary.model.isin(MODELS)].set_index('model')
        accuracy=s.mae_eur_mwh.idxmin();money=s.net_margin_eur.idxmax()
        findings.append(f'- {z}: lower MAE came from **{accuracy}**; higher net margin came from **{money}**. '+('The rankings differ in this sample.' if accuracy!=money else 'The rankings agree in this sample.'))
    report='''# Historical forecast baselines: accuracy versus battery margin

## What we did and why

We replaced perfect future prices in the battery decision with two transparent historical forecasts. We then froze the resulting charge/discharge schedule and valued it using actual prices. This isolates how price information changes financial decisions while holding the physical model constant.

The test covers **9 January–31 December 2024: 358 days and 8,592 hours per zone**. The first eight local days supply history. All strategies, including the oracle, are evaluated on exactly this period; do not compare these totals directly with the earlier full-year oracle totals.

## Information timing and forecast definition

For delivery day D, we define an experimental decision cutoff of **09:00 local time on D-1**. This is a chosen modelling cutoff, not a verified exchange gate-closure rule. We conservatively use only complete delivery days **D-8 through D-2**, even though some newer day-ahead prices may already be known. Historical exports lack publication-vintage metadata, so the backtest assumes prices for fully elapsed delivery days were available and unchanged at the cutoff. This assumption is not independently verified.

- **Latest same hour:** use the most recent observed daily price for the target local hour in that history, normally D-2. If that hour is absent due to spring DST, fall back to the previous available day.
- **Seven-day same hour:** average the daily same-hour values over those seven days. A repeated autumn hour is averaged within its historical day first, giving each day equal weight. A missing spring hour is omitted. Both repeated target autumn hours receive the same forecast.

No target-day actual demand, generation, prices or spreads enter the forecast. Every source delivery interval ends before the cutoff. Tests verify that changing data after the historical boundary cannot change the forecast.

## Battery decisions and settlement

The Pyomo/HiGHS model and assumptions are unchanged: 1 MW / 2 MWh, 90% round-trip efficiency, EUR 10 per grid-side MWh discharged, 50% starting/terminal SOC each day, no simultaneous charge/discharge. All quantities are assumed accepted at actual day-ahead prices. This remains a simplified price-taking auction experiment, without bid rejection, market impact, fees, imbalance costs or intraday adjustment.

The optimiser maximises expected net margin at forecast prices. Settlement applies actual prices to those fixed quantities. Realised daily losses are retained; we never retrospectively cancel an unprofitable day. Forecast-based optimisation's nonnegative expected margin is not a guarantee of nonnegative realised margin.

## Results

'''+table(summary[['zone','model','mae_eur_mwh','net_margin_eur','oracle_gap_eur','worst_day_eur','loss_days']].round(2))+'''

All margins are EUR per illustrative battery, after assumed cycling cost and before other costs. MAE is hourly weighted in EUR/MWh. Oracle MAE is zero by construction, not predictive skill.

'''+ '\n'.join(findings)+'''

These are descriptive results from one retrospectively studied year, not a universal ranking or an untouched investment validation set. Neither baseline was tuned to maximise these reported results. Future ML needs a separately defined chronological validation/test protocol.

![Cumulative margins](figures/forecast_margins_2024.svg)

## Extreme-event diagnostics

We use a fixed illustrative spike threshold **strictly above EUR 200/MWh**, and negative prices **strictly below zero**. These definitions were chosen for this experiment, not tuned as a trading trigger. Precision is true events divided by predicted events; recall is detected events divided by actual events. Undefined ratios are left missing, not replaced with zero.

'''+table(summary[summary.model!='perfect_foresight'][['zone','model','spike_precision','spike_recall','actual_spike_hours','negative_precision','negative_recall','actual_negative_hours']].round(3))+'''

Ratios are fractions between zero and one. Event prediction is distinct from financial capture: battery SOC and charge/discharge constraints also determine which opportunities can be used. Event metrics alone do not establish why one strategy earned more.

## Checks and reproducibility

We solved 2,148 daily problems (two forecasts plus the oracle, for 358 days in each zone). Every schedule passes the existing physical checks. Settlement leaves its quantities and SOC unchanged, and its actual net margin never exceeds the same-day oracle beyond numerical tolerance. Both DST transition days are included. The French missing actual-fundamentals hour does not matter because these baselines use prices only. The German Sequence 1 metadata limitation remains as documented in the earlier price report.

```bash
python scripts/analyse_forecasts.py
PYTHONPATH=src python -m unittest discover -s tests
```

First run the fundamentals pipeline if the processed price dataset is absent. Full dispatch and per-day information-cutoff audit are written to git-ignored `data/processed/forecast_dispatch_2024.csv` and `forecast_timing_2024.csv`.

Published outputs: [summary](forecast_summary_2024.csv), [daily results](forecast_daily_2024.csv), [12 December schedules and settlement](forecast_dispatch_2024-12-12.csv), [validation metadata](forecast_validation_2024.json).

## What comes next and why

Inspect loss days and missed extremes before adding model complexity. Then define a chronological ML experiment with only available features and compare against these baselines on the same held-out dates. The purpose is to test whether additional forecasting skill improves net battery decisions, not merely to reduce average prediction error. Keep documenting changes to the information set, constraints and costs.
'''
    (out/'forecast_baselines_2024.md').write_text(report)
    audit={'battery':asdict(battery),'evaluation_local_start':'2024-01-09','evaluation_local_end_inclusive':'2024-12-31','days_per_zone':358,'hours_per_zone':8592,'solves':2148,'spike_threshold_eur_mwh':200,'decision_cutoff':'D-1 09:00 Europe/Berlin','historical_delivery_days':'D-8 through D-2','input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'dispatch_unchanged_at_settlement':True,'oracle_dominance_passed':True,'max_source_end_utc':timing.latest_source_delivery_end_utc.max()}
    (out/'forecast_validation_2024.json').write_text(json.dumps(audit,indent=2))
    print(summary[['zone','model','mae_eur_mwh','net_margin_eur','oracle_gap_eur','loss_days']].to_string(index=False));return summary
if __name__=='__main__':run()
