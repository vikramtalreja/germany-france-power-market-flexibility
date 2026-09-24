"""Reproduce the retrospective December case study from the validated hourly dataset."""
from pathlib import Path
import hashlib
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CORE = ['price_eur_mwh','demand_mw','wind_mw','solar_mw','residual_load_mw']

def run():
    source = ROOT/'data/processed/fundamentals_prices_2024_hourly.csv'
    if not source.exists():
        raise FileNotFoundError('Run python scripts/analyse_fundamentals.py first.')
    all_data = pd.read_csv(source)
    all_data['timestamp_utc'] = pd.to_datetime(all_data.timestamp_utc, utc=True)
    local = all_data.timestamp_utc.dt.tz_convert('Europe/Berlin')
    dec = all_data[(local.dt.year == 2024) & (local.dt.month == 12)].copy()
    dec['timestamp_cet'] = dec.timestamp_utc.dt.tz_convert('Europe/Berlin')
    expected = pd.date_range('2024-12-01', '2025-01-01', freq='h', inclusive='left', tz='Europe/Berlin').tz_convert('UTC')
    for zone in ['DE-LU','FR']:
        f = dec[dec.zone.eq(zone)].sort_values('timestamp_utc')
        assert pd.DatetimeIndex(f.timestamp_utc).equals(expected), zone
        assert f[CORE].notna().all().all(), zone
        assert (f.demand_mw-f.wind_mw-f.solar_mw-f.residual_load_mw).abs().max()<1e-6
    out=ROOT/'reports'; (out/'figures').mkdir(parents=True,exist_ok=True)
    prices=dec.pivot(index='timestamp_utc', columns='zone', values='price_eur_mwh').sort_index()
    prices['spread_de_minus_fr_eur_mwh']=prices['DE-LU']-prices.FR
    prices['timestamp_cet']=prices.index.tz_convert('Europe/Berlin')
    prices.to_csv(out/'december_hourly_spreads_2024.csv')
    daily=prices[['DE-LU','FR','spread_de_minus_fr_eur_mwh']].copy()
    daily.index=daily.index.tz_convert('Europe/Berlin')
    daily=daily.resample('D').mean();daily.index.name='day_cet'
    daily.to_csv(out/'december_daily_spreads_2024.csv')
    top=pd.concat([dec[dec.zone.eq(z)].sort_values(['price_eur_mwh','timestamp_utc'],ascending=[False,True]).head(20) for z in ['DE-LU','FR']])
    top=top[['zone','timestamp_utc','timestamp_cet']+CORE].merge(prices[['spread_de_minus_fr_eur_mwh']],left_on='timestamp_utc',right_index=True,validate='many_to_one')
    top.to_csv(out/'december_top20_hours_2024.csv',index=False)
    peak=dec[dec.zone.eq('DE-LU')].sort_values('price_eur_mwh').iloc[-1]
    event_time=peak.timestamp_utc
    comparisons=[]
    for z in ['DE-LU','FR']:
        f=dec[dec.zone.eq(z)]; event=f[f.timestamp_utc.eq(event_time)].iloc[0]
        for label,b in [('other_december_hours',f[~f.timestamp_utc.eq(event_time)]),('other_december_17h_weekdays',f[(f.timestamp_cet.dt.hour==17)&(f.timestamp_cet.dt.dayofweek<5)&(~f.timestamp_utc.eq(event_time))])]:
            for c in CORE:
                comparisons.append(dict(zone=z,baseline=label,metric=c,event_value=event[c],baseline_median=b[c].median(),baseline_hours=len(b),share_baseline_at_or_below_event_pct=100*b[c].le(event[c]).mean()))
    comparison=pd.DataFrame(comparisons);comparison.to_csv(out/'december_peak_comparison_2024.csv',index=False)
    summary=dec.groupby('zone').agg(hours=('price_eur_mwh','size'),mean_price=('price_eur_mwh','mean'),min_price=('price_eur_mwh','min'),max_price=('price_eur_mwh','max'),negative_hours=('price_eur_mwh',lambda x:int((x<0).sum())))
    summary.to_csv(out/'december_summary_2024.csv')
    window=dec[(dec.timestamp_cet>=pd.Timestamp('2024-12-10',tz='Europe/Berlin'))&(dec.timestamp_cet<pd.Timestamp('2024-12-15',tz='Europe/Berlin'))]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'december2024'})
    fig,axes=plt.subplots(4,1,figsize=(12,12),sharex=True)
    for z,color in [('DE-LU','#215D9C'),('FR','#C96532')]:
        f=window[window.zone.eq(z)].sort_values('timestamp_utc'); t=f.timestamp_cet
        axes[0].plot(t,f.price_eur_mwh,label=z,color=color)
        axes[1].plot(t,f.demand_mw/1000,label=z+' demand',color=color)
        axes[1].plot(t,f.residual_load_mw/1000,label=z+' residual load',color=color,ls='--')
        axes[2].plot(t,f.wind_mw/1000,label=z+' wind',color=color)
        axes[2].plot(t,f.solar_mw/1000,label=z+' solar',color=color,ls=':')
    w=prices[(prices.timestamp_cet>=pd.Timestamp('2024-12-10',tz='Europe/Berlin'))&(prices.timestamp_cet<pd.Timestamp('2024-12-15',tz='Europe/Berlin'))]
    axes[3].plot(w.timestamp_cet,w.spread_de_minus_fr_eur_mwh,color='#62468a',label='DE-LU minus France')
    axes[3].axhline(0,color='grey',lw=.7)
    for ax,label in zip(axes,['Price (EUR/MWh)','Demand / residual (GW)','Wind / solar (GW)','Spread (EUR/MWh)']):
        ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(loc='upper left',ncol=2,fontsize=9)
        ax.axvline(event_time,color='black',ls='--',lw=.8,alpha=.5)
    axes[0].annotate(f'{peak.price_eur_mwh:.2f} EUR/MWh\n12 Dec, 17:00 CET',xy=(event_time,peak.price_eur_mwh),xytext=(22,-12),textcoords='offset points',va='top',fontsize=10)
    axes[3].xaxis.set_major_locator(mdates.DayLocator(tz=ZoneInfo('Europe/Berlin')))
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter('%d Dec',tz=ZoneInfo('Europe/Berlin')))
    axes[3].set_xlabel('Delivery time (CET, UTC+1); hourly interval starts')
    fig.suptitle('December 2024 | German price spike and market fundamentals',fontsize=16,weight='bold')
    fig.text(.07,.013,'Actual observations: retrospective context, not auction-time forecasts. Residual load = demand − wind − solar.',fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.965))
    for ext in ['svg','png']:fig.savefig(out/f'figures/december_case_2024.{ext}',dpi=140,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    def table(df):
        return '| '+' | '.join(map(str,df.columns))+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f'{x:,.2f}' if isinstance(x,float) else str(x) for x in row)+' |' for row in df.itertuples(index=False,name=None))
    event=dec[dec.timestamp_utc.eq(event_time)].set_index('zone')
    e=event.loc['DE-LU'];fr=event.loc['FR']; spread=prices.loc[event_time,'spread_de_minus_fr_eur_mwh']
    baseline=comparison[(comparison.zone=='DE-LU')&(comparison.baseline=='other_december_17h_weekdays')].set_index('metric')
    report=f'''# December 2024: a German price spike in a wider European context

**Finding:** at 17:00–18:00 CET on 12 December, the supplied DE-LU price series reached **EUR {e.price_eur_mwh:,.2f}/MWh**, while France was **EUR {fr.price_eur_mwh:,.2f}/MWh**. The contemporaneous spread was **EUR {spread:,.2f}/MWh**. German actual wind and solar totalled **{(e.wind_mw+e.solar_mw)/1000:.2f} GW**, leaving **{e.residual_load_mw/1000:.2f} GW** of demand after subtracting these two sources.

![Prices and actual fundamentals, 10–14 December](figures/december_case_2024.svg)

## Peak-hour observations

{table(event[CORE].reset_index().round(2))}

Power columns are MW; prices are EUR/MWh. Residual load excludes only wind and solar, not nuclear, hydro or other generation. These are national fundamentals paired with zonal prices (Germany versus DE-LU).

Against the **other December weekdays at 17:00 CET**, German median demand was **{baseline.loc['demand_mw','baseline_median']/1000:.2f} GW**, wind **{baseline.loc['wind_mw','baseline_median']/1000:.2f} GW**, solar **{baseline.loc['solar_mw','baseline_median']/1000:.2f} GW**, and residual load **{baseline.loc['residual_load_mw','baseline_median']/1000:.2f} GW**. The matched comparison contains {int(baseline.iloc[0].baseline_hours)} hours and controls for time of day and weekday status, but not weather, holidays or outages.

The event residual load was at or above **{baseline.loc['residual_load_mw','share_baseline_at_or_below_event_pct']:.1f}%** of those matched hours. Low wind/solar output alongside substantial demand is consistent with greater demand for other generation and imports. This is an interpretation of observed conditions, not a causal decomposition of the auction price.

## Month-wide context

{table(summary.reset_index().round(2))}

December mean DE-LU minus France spread: **EUR {prices.spread_de_minus_fr_eur_mwh.mean():.2f}/MWh**. Negative hours count prices strictly below zero. Top-20 tables rank December separately for each zone; ties are ordered by UTC timestamp. The plotted five-day event window was selected retrospectively around the German annual maximum and is not an unbiased forecasting test.

## What is supported, and what remains unknown

- The supplied data establishes the coincident price divergence and actual demand/renewable conditions. France's residual load cannot be interpreted as scarcity without accounting for its other generation, including nuclear.
- Actual generation and demand were not available at the preceding auction. They contextualise delivery conditions, but do not reconstruct participants' expectations.
- A large price spread does not establish the binding network constraint, the direction or volume of physical flows, or an FBMC effect. Cross-border capacity, network constraints and auction outcomes are needed.
- Generator outages, available capacity, fuel/carbon costs and submitted bids have not been analysed. We cannot attribute the spike to a particular marginal generator, strategic bidding or physical shortage.
- The German export uses Sequence 1 as in the existing pipeline; its precise auction metadata remains pending confirmation. Findings are conditional on that selection.

## Data, validation and reproduction

Inputs are the existing validated hourly price/fundamentals dataset built from user-supplied ENTSO-E price exports, SMARD actuals and RTE eco2mix actuals. See [the fundamentals report](fundamentals_2024.md) for provenance, source definitions and the French DST gap. That gap is outside December.

December contains **744 unique, complete hours per zone**, with no missing core inputs. The plot contains 120 hours per zone. Filtering uses local delivery dates; joins use UTC. Daily spreads are arithmetic means of the 24 hourly spreads, not price ratios. No missing values are filled.

```bash
python scripts/analyse_fundamentals.py  # if the processed file is absent
python scripts/analyse_december.py
```

The second command recreates this report, the chart and these tables:

- [Top 20 hours per zone](december_top20_hours_2024.csv)
- [Hourly spreads](december_hourly_spreads_2024.csv)
- [Daily mean spreads](december_daily_spreads_2024.csv)
- [Event-versus-baseline comparison](december_peak_comparison_2024.csv)
- [Monthly summary](december_summary_2024.csv)

## Implication for the next experiment

This episode motivates testing whether price forecasts capture financially important extremes. It does not demonstrate a profitable battery strategy. Next build the 1 MW / 2 MWh perfect-foresight benchmark with explicit efficiency, cycling and terminal-energy assumptions; then compare forecast-driven schedules under identical constraints.
'''
    (out/'december_case_2024.md').write_text(report)
    audit={'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'december_hours_per_zone':744,'plot_hours_per_zone':120,'top_hours_per_zone':20,'event_utc':str(event_time),'event_cet':str(peak.timestamp_cet),'checks':'unique continuous hourly coverage; complete core columns; residual-load identity'}
    assert len(top)==40 and len(daily)==31 and len(window)==240
    (out/'december_validation_2024.json').write_text(json.dumps(audit,indent=2))
    print(summary.to_string());print(event[CORE].to_string());print('Spread:',spread)
    return summary, comparison

if __name__=='__main__':run()
