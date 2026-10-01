"""Features and small candidate set for the predeclared chronological protocol."""
from datetime import timedelta
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from market_flex.forecast import forecast

NUMERIC=['hour_sin','hour_cos','latest_same_hour','seven_day_same_hour_mean','seven_day_same_hour_std_ddof0','seven_day_same_hour_min','seven_day_same_hour_max','mean_of_seven_daily_mean_prices']
WEEKDAYS=[f'weekday_{i}' for i in range(7)]

def day_features(prices,target):
    latest,audit=forecast(prices,target,'latest_same_hour')
    mean,_=forecast(prices,target,'seven_day_same_hour')
    history=prices[(prices.index>=pd.Timestamp(audit['history_start_utc']))&(prices.index<pd.Timestamp(audit['history_end_exclusive_utc']))]
    local=history.index.tz_convert('Europe/Berlin')
    h=pd.DataFrame({'price':history,'day':local.date,'hour':local.hour})
    daily=h.groupby(['day','hour']).price.mean().reset_index()
    grouped=daily.groupby('hour').price
    target_local=target.tz_convert('Europe/Berlin');hour=target_local.hour
    f=pd.DataFrame(index=target)
    f['hour_sin']=np.sin(2*np.pi*hour/24);f['hour_cos']=np.cos(2*np.pi*hour/24)
    f['latest_same_hour']=latest;f['seven_day_same_hour_mean']=mean
    for name,profile in [('std_ddof0',grouped.std(ddof=0)),('min',grouped.min()),('max',grouped.max())]:
        f['seven_day_same_hour_'+name]=profile.reindex(hour).to_numpy()
    f['mean_of_seven_daily_mean_prices']=h.groupby('day').price.mean().mean()
    for i in range(7):f[f'weekday_{i}']=(target_local.dayofweek==i).astype(float)
    assert np.isfinite(f.to_numpy()).all()
    return f[NUMERIC+WEEKDAYS],audit

def feature_matrix(prices):
    frames=[];audits=[]
    for day,g in prices.groupby(prices.index.tz_convert('Europe/Berlin').date):
        if day<pd.Timestamp('2024-01-09').date():continue
        f,a=day_features(prices,g.index);frames.append(f);audits.append({'day_cet':str(day),**a})
    return pd.concat(frames),pd.DataFrame(audits)

def mask(index,window):
    dates=index.tz_convert('Europe/Berlin').strftime('%Y-%m-%d')
    return (dates>=window['start'])&(dates<=window['end'])

def candidates(config):
    result={}
    ridge,forest=config['candidates']
    for alpha in ridge['alpha']:
        result[f'ridge_alpha_{alpha}']={'family':'ridge','alpha':alpha}
    for depth in forest['max_depth']:
        for leaf in forest['min_samples_leaf']:
            result[f'rf_depth_{depth}_leaf_{leaf}']={'family':'random_forest','n_estimators':forest['n_estimators'],'max_depth':depth,'min_samples_leaf':leaf,'max_features':float(forest['max_features']),'random_state':forest['random_state'],'n_jobs':forest['n_jobs']}
    return result

def estimator(spec):
    if spec['family']=='ridge':
        preprocessing=ColumnTransformer([('numeric',StandardScaler(),NUMERIC),('weekday','passthrough',WEEKDAYS)])
        return Pipeline([('features',preprocessing),('model',Ridge(alpha=spec['alpha']))])
    return RandomForestRegressor(**{k:v for k,v in spec.items() if k!='family'})

def select(summary,order,tolerance=1.):
    contenders=summary[summary.net_margin_eur>=summary.net_margin_eur.max()-tolerance].copy()
    contenders['order']=contenders.model.map({m:i for i,m in enumerate(order)})
    return contenders.sort_values(['mae_eur_mwh','order']).iloc[0].model

def assert_training_boundary(training_index,first_delivery_day):
    last_day=pd.Timestamp(first_delivery_day).date()-timedelta(days=2)
    assert max(training_index.tz_convert('Europe/Berlin').date)<=last_day
