"""Reconcile forecast-strategy differences and inspect retrospective failures."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
A='latest_same_hour';B='seven_day_same_hour';O='perfect_foresight'

def table(df):
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f'{v:,.2f}' if isinstance(v,float) else str(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))

def run():
    source=ROOT/'data/processed/forecast_dispatch_2024.csv';h=pd.read_csv(source)
    h.timestamp_utc=pd.to_datetime(h.timestamp_utc,utc=True)
    assert not h.duplicated(['zone','model','timestamp_utc']).any()
    assert h.groupby(['zone','model']).size().eq(8592).all()
    h['sales_eur']=h.actual_eur_mwh*h.discharge_mw
    h['purchases_eur']=h.actual_eur_mwh*h.charge_mw
    assert np.allclose(h.sales_eur-h.purchases_eur-h.degradation_eur,h.net_margin_eur)
    out=ROOT/'reports';totals=h.groupby(['zone','model'])[['sales_eur','purchases_eur','degradation_eur','net_margin_eur','charge_mw','discharge_mw']].sum()
    totals['weighted_sell_price']=totals.sales_eur/totals.discharge_mw
    totals['weighted_buy_price']=totals.purchases_eur/totals.charge_mw
    totals.to_csv(out/'failure_strategy_totals_2024.csv')
    contributions=[];decomposition=[];regimes=[];events=[];selected=[];comparisons=[]
    daily=h.groupby(['zone','model','day_cet']).agg(sales_eur=('sales_eur','sum'),purchases_eur=('purchases_eur','sum'),degradation_eur=('degradation_eur','sum'),net_margin_eur=('net_margin_eur','sum'),forecast_net_margin_eur=('forecast_net_margin_eur','sum'),gross_margin_eur=('gross_margin_eur','sum'),discharge_mwh=('discharge_mw','sum'))
    daily['forecast_optimism_eur']=daily.forecast_net_margin_eur-daily.net_margin_eur
    losses=daily[daily.net_margin_eur<-1e-6].reset_index()
    losses.to_csv(out/'failure_loss_days_2024.csv',index=False)
    for z in ['DE-LU','FR']:
        a=totals.loc[(z,A)];b=totals.loc[(z,B)];gap=b.net_margin_eur-a.net_margin_eur
        row=dict(zone=z,additional_sales_eur=b.sales_eur-a.sales_eur,additional_purchases_eur=b.purchases_eur-a.purchases_eur,additional_degradation_eur=b.degradation_eur-a.degradation_eur,net_advantage_eur=gap)
        assert abs(row['additional_sales_eur']-row['additional_purchases_eur']-row['additional_degradation_eur']-gap)<1e-6
        contributions.append(row)
        # Exact symmetric midpoint identity: change(P*Q)=mean(P)*change(Q)+mean(Q)*change(P).
        effects={
            'discharge_volume':(b.discharge_mw-a.discharge_mw)*(b.weighted_sell_price+a.weighted_sell_price)/2,
            'discharge_price_mix':(b.weighted_sell_price-a.weighted_sell_price)*(b.discharge_mw+a.discharge_mw)/2,
            'charge_volume':-(b.charge_mw-a.charge_mw)*(b.weighted_buy_price+a.weighted_buy_price)/2,
            'charge_price_mix':-(b.weighted_buy_price-a.weighted_buy_price)*(b.charge_mw+a.charge_mw)/2,
            'cycling_cost':-(b.degradation_eur-a.degradation_eur)}
        assert abs(sum(effects.values())-gap)<1e-6
        for name,value in effects.items():decomposition.append(dict(zone=z,component=name,contribution_eur=value))
        aa=h[(h.zone==z)&(h.model==A)].set_index('timestamp_utc');bb=h[(h.zone==z)&(h.model==B)].set_index('timestamp_utc');oo=h[(h.zone==z)&(h.model==O)].set_index('timestamp_utc')
        assert aa.index.equals(bb.index) and aa.index.equals(oo.index)
        assert np.allclose(aa.actual_eur_mwh,bb.actual_eur_mwh)
        price=aa.actual_eur_mwh
        for name,mask in [('negative',price<0),('ordinary_0_to_200',(price>=0)&(price<=200)),('spike_above_200',price>200)]:
            regimes.append(dict(zone=z,regime=name,hours=int(mask.sum()),net_advantage_eur=float((bb.net_margin_eur-aa.net_margin_eur)[mask].sum())))
        for model,f in [(A,aa),(B,bb)]:
            for name,mask,predicted in [('spike_above_200',price>200,f.forecast_eur_mwh>200),('negative',price<0,f.forecast_eur_mwh<0)]:
                missed=mask&~predicted
                events.append(dict(zone=z,model=model,event=name,actual_hours=int(mask.sum()),missed_hours=int(missed.sum()),missed_hours_discharging=int((missed&(f.discharge_mw>1e-6)).sum()),missed_hours_charging=int((missed&(f.charge_mw>1e-6)).sum()),discharge_mwh_on_missed=float(f.discharge_mw[missed].sum()),charge_mwh_on_missed=float(f.charge_mw[missed].sum()),oracle_discharge_mwh_on_same_hours=float(oo.discharge_mw[missed].sum()),oracle_charge_mwh_on_same_hours=float(oo.charge_mw[missed].sum())))
        da=daily.loc[(z,A)];db=daily.loc[(z,B)];delta=db.net_margin_eur-da.net_margin_eur
        comparisons.append(dict(zone=z,seven_day_wins=int((delta>1e-6).sum()),latest_wins=int((delta<-1e-6).sum()),ties=int((delta.abs()<=1e-6).sum()),best_five_advantage_eur=float(delta.nlargest(5).sum()),worst_five_advantage_eur=float(delta.nsmallest(5).sum())))
        for kind,date in [('worst_seven_day_loss',db.net_margin_eur.idxmin()),('largest_seven_day_underperformance',delta.idxmin()),('largest_seven_day_advantage',delta.idxmax())]:
            for model in [A,B,O]:
                row=daily.loc[(z,model,date)].to_dict();selected.append(dict(zone=z,case=kind,day_cet=date,model=model,**row))
    contributions=pd.DataFrame(contributions);decomposition=pd.DataFrame(decomposition);regimes=pd.DataFrame(regimes);events=pd.DataFrame(events);selected=pd.DataFrame(selected);comparisons=pd.DataFrame(comparisons)
    assert np.allclose(regimes.groupby('zone').net_advantage_eur.sum(),contributions.set_index('zone').net_advantage_eur)
    for name,df in [('attribution',contributions),('decomposition',decomposition),('regimes',regimes),('events',events),('selected_cases',selected),('daily_comparison',comparisons)]:df.to_csv(out/f'failure_{name}_2024.csv',index=False)
    selkeys=selected[['zone','day_cet']].drop_duplicates()
    details=h.merge(selkeys,on=['zone','day_cet'],how='inner');details.to_csv(out/'failure_case_dispatch_2024.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'failures2024'})
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,z in zip(axes,['DE-LU','FR']):
        r=contributions[contributions.zone==z].iloc[0]
        vals=[r.additional_sales_eur,-r.additional_purchases_eur,-r.additional_degradation_eur,r.net_advantage_eur]
        ax.bar(['Sales\nincrease','Extra\npurchases','Extra\ncycling cost','Net\nadvantage'],np.array(vals)/1000,color=['#215D9C','#C96532','#C96532','#37826a'])
        ax.axhline(0,color='grey',lw=.8);ax.set_title(z,loc='left',weight='bold');ax.set_ylabel('Difference (EUR thousands)');ax.grid(axis='y',alpha=.15)
    fig.suptitle('Why the seven-day schedule earned more | Accounting reconciliation',fontsize=14,weight='bold')
    fig.text(.07,.015,'Seven-day minus latest-same-hour; 9 Jan–31 Dec 2024. Descriptive accounting, not causal model attribution.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95))
    for ext in ['svg','png']:fig.savefig(out/f'figures/failure_attribution_2024.{ext}',dpi=140,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    narrative=[]
    for z in ['DE-LU','FR']:
        b=totals.loc[(z,B)];a=totals.loc[(z,A)];c=contributions[contributions.zone==z].iloc[0]
        loss=selected[(selected.zone==z)&(selected.case=='worst_seven_day_loss')&(selected.model==B)].iloc[0]
        e=events[(events.zone==z)&(events.model==B)&(events.event=='spike_above_200')].iloc[0]
        loss_hours=h[(h.zone==z)&(h.model==B)&(h.day_cet==loss.day_cet)].copy()
        loss_hours['shortfall_eur']=loss_hours.forecast_net_margin_eur-loss_hours.net_margin_eur
        loss_hours['delivery_local']=loss_hours.timestamp_utc.dt.tz_convert('Europe/Berlin').astype(str)
        top_errors=table(loss_hours.nlargest(3,'shortfall_eur')[['delivery_local','forecast_eur_mwh','actual_eur_mwh','charge_mw','discharge_mw','shortfall_eur']].round(2))
        narrative.append(f'''### {z}

The seven-day strategy discharged **{b.discharge_mw:.2f} MWh** versus **{a.discharge_mw:.2f} MWh** for the latest-hour strategy. Its weighted sale price was **EUR {b.weighted_sell_price:.2f}/MWh** versus **{a.weighted_sell_price:.2f}**, and weighted purchase price **EUR {b.weighted_buy_price:.2f}/MWh** versus **{a.weighted_buy_price:.2f}**. These are quantity-weighted prices of the selected transactions, not market-wide means.

Additional sales of **EUR {c.additional_sales_eur:.2f}**, minus extra purchases of **EUR {c.additional_purchases_eur:.2f}** and cycling costs of **EUR {c.additional_degradation_eur:.2f}**, explain the **EUR {c.net_advantage_eur:.2f}** net advantage exactly. More trading alone is not a sufficient explanation; prices and quantities both changed.

Its worst loss was **{loss.day_cet}**: expected net margin **EUR {loss.forecast_net_margin_eur:.2f}**, actual gross margin **EUR {loss.gross_margin_eur:.2f}**, cycling cost **EUR {loss.degradation_eur:.2f}**, and realised net **EUR {loss.net_margin_eur:.2f}**. The expected opportunity failed to cover the realised cost of cycling.

Largest adverse settlement surprises on that loss day:

{top_errors}

Shortfall is (forecast price - actual price) multiplied by net export; positive values reduce realised margin relative to forecast. These are selected adverse intervals, not the complete day.

It missed the EUR 200 threshold in **{int(e.missed_hours)} of {int(e.actual_hours)} actual spike hours**, but still discharged during **{int(e.missed_hours_discharging)}** of those missed hours. Predicting a price below 200 can still produce discharge if that hour is relatively attractive within the forecast profile.
''')
    report='''# Why the seven-day forecast earned more, and where it failed

## Scope and method

This is a retrospective diagnosis of the existing schedules; no forecasts are changed and no model is tuned. We reconcile the seven-day-minus-latest margin difference exactly, inspect losing days, and distinguish threshold detection from physical action. The common period is 9 January–31 December 2024.

## What the accounting establishes

'''+table(contributions.round(2))+'''

![Margin reconciliation](figures/failure_attribution_2024.svg)

'''+ '\n'.join(narrative)+'''
## Separating trading volume and selected prices

'''+table(decomposition.round(2))+'''

For both purchases and sales we use the exact identity change(P*Q) = mean(P)*change(Q) + mean(Q)*change(P), where P is the transaction-weighted price and Q is energy. Purchase components enter with a minus sign. This symmetric decomposition separates volume from selected-price mix without arbitrary ordering. It is an arithmetic attribution, not evidence that smoothing alone caused a particular improvement. Weighted prices and volumes are jointly determined by whole-day schedules.

## Which hours account for the difference?

'''+table(regimes.round(2))+'''

These are interval-level accounting contributions, including cycling cost on discharge. They sum to the total difference. They are not standalone regime profits: charging in one regime may support discharge in another, and shifting boundaries would shift the accounting attribution.

'''+table(comparisons.round(2))+'''

## Failure cases worth studying

'''+table(selected[['zone','case','day_cet','model','forecast_net_margin_eur','gross_margin_eur','degradation_eur','net_margin_eur']].round(2))+'''

Worst absolute loss and largest underperformance against the other baseline are different questions. The oracle shows that a profitable schedule could exist even when the selected forecast schedule loses. Forecast optimism is forecast-valued net margin minus actual-valued net margin for the same fixed actions; it is not a causal forecast-error decomposition.

## Missed extremes are not necessarily missed actions

'''+table(events[['zone','model','event','actual_hours','missed_hours','missed_hours_discharging','missed_hours_charging']])+'''

Spikes are prices strictly above EUR 200/MWh; negatives are strictly below zero, as in the original experiment. The optimiser reacts to the entire relative price profile, losses and cycling costs, not these diagnostic thresholds. A missed spike classification can coincide with discharge; a missed negative-price classification can coincide with charging. Neither action guarantees a good whole-day result. Oracle volumes on identical missed-event hours are available in the event CSV, but do not by themselves establish achievable incremental profit because SOC couples intervals.

## What we can and cannot conclude

The seven-day schedules earned more through a combination of different quantities and transaction prices; the tables identify those arithmetic contributions. A plausible interpretation is that averaging stabilises a useful daily price shape, but that mechanism has not been isolated experimentally. Do not claim that lower spike recall caused higher profit, or that a less accurate forecast won: the seven-day forecast also had lower MAE in this sample.

The loss cases demonstrate that a positive forecast-valued spread may be inadequate after actual prices and cycling costs. The next model should be evaluated on decision outcomes as well as MAE. Any filter inspired by these failures must be developed on training/validation dates and tested elsewhere; deleting these loss days retrospectively would bias results.

All earlier assumptions remain: historical price vintages unverified, German Sequence 1 metadata pending, fully accepted price-taking trades, daily SOC reset, and other operating/investment costs excluded. These are simulated margins, not demonstrated live trading profit.

## Reproduction and next step

```bash
python scripts/analyse_forecasts.py  # if full dispatch is absent
python scripts/analyse_failures.py
```

The analysis checks interval accounting, paired timestamps, the exact volume/price reconciliation, and the sum of price-regime contributions. Published CSVs use the `failure_` prefix, including [all losing days](failure_loss_days_2024.csv), [selected hourly schedules](failure_case_dispatch_2024.csv), [extreme-event actions](failure_events_2024.csv) and [price/volume decomposition](failure_decomposition_2024.csv).

Before ML, define a chronological evaluation split. Use these retrospective cases to formulate hypotheses about daily shape and uneconomic cycling, not to cherry-pick a strategy. A later controlled comparison should assess whether new features improve schedule timing and realised net margin on dates not used to develop them.
'''
    (out/'forecast_failures_2024.md').write_text(report)
    (out/'failure_validation_2024.json').write_text(json.dumps({'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'paired_hours_per_zone':8592,'accounting_reconciled':True,'volume_price_decomposition_reconciled':True,'regime_contributions_reconciled':True,'new_optimisations':0},indent=2))
    print(contributions.round(2).to_string(index=False));print(decomposition.round(2).to_string(index=False));print(regimes.round(2).to_string(index=False));print(events.to_string(index=False));return contributions
if __name__=='__main__':run()
