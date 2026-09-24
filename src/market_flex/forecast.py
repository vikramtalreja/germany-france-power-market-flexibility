"""Conservative historical price baselines with explicit decision cutoffs."""
from datetime import timedelta
import numpy as np
import pandas as pd

MODELS=('latest_same_hour','seven_day_same_hour')

def forecast(prices,target_index,model):
    if model not in MODELS:raise ValueError(model)
    if prices.index.tz is None or target_index.tz is None:raise ValueError('Timezone-aware timestamps required')
    local=target_index.tz_convert('Europe/Berlin')
    days=set(local.date)
    if len(days)!=1:raise ValueError('Forecast one local day at a time')
    day=local[0].date()
    # Experiment cutoff, not a claim about exchange rules. Use only fully elapsed days.
    cutoff=pd.Timestamp(str(day-timedelta(days=1))+' 09:00',tz='Europe/Berlin')
    start=pd.Timestamp(day-timedelta(days=8),tz='Europe/Berlin').tz_convert('UTC')
    end=pd.Timestamp(day-timedelta(days=1),tz='Europe/Berlin').tz_convert('UTC')
    history=prices[(prices.index>=start)&(prices.index<end)].sort_index()
    expected=pd.date_range(start,end,freq='h',inclusive='left')
    if not history.index.equals(expected) or not np.isfinite(history).all():raise ValueError('Need seven complete historical local days D-8 through D-2')
    assert (history.index+pd.Timedelta(hours=1)<=cutoff).all()
    h=pd.DataFrame({'price':history,'date':history.index.tz_convert('Europe/Berlin').date,'hour':history.index.tz_convert('Europe/Berlin').hour})
    # Repeated autumn hour has one daily mean; a missing spring hour has no observation.
    daily=h.groupby(['date','hour']).price.mean().reset_index()
    if model=='latest_same_hour':profile=daily.sort_values('date').groupby('hour').price.last()
    else:profile=daily.groupby('hour').price.mean()
    values=[profile.loc[hour] for hour in local.hour]
    prediction=pd.Series(values,index=target_index,name='forecast_eur_mwh')
    return prediction,{'decision_cutoff_utc':str(cutoff.tz_convert('UTC')),'history_start_utc':str(start),'history_end_exclusive_utc':str(end),'latest_source_delivery_end_utc':str(history.index[-1]+pd.Timedelta(hours=1))}

def settle(schedule,actual):
    """Fix quantities chosen using forecast prices; apply actual settlement prices."""
    if not schedule.index.equals(actual.index) or not np.isfinite(actual).all():raise ValueError('Actual prices must exactly align')
    result=schedule.copy().rename(columns={'price_eur_mwh':'forecast_eur_mwh','net_margin_eur':'forecast_net_margin_eur','gross_margin_eur':'forecast_gross_margin_eur'})
    result['actual_eur_mwh']=actual
    result['gross_margin_eur']=actual*(result.discharge_mw-result.charge_mw)
    result['net_margin_eur']=result.gross_margin_eur-result.degradation_eur
    return result
