"""Frozen transfer test. Source comparability gate precedes 2025 acquisition/scoring."""
from pathlib import Path
import sys,json,hashlib,urllib.request
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pandas as pd
from market_flex.ml import feature_matrix,day_features,mask,candidates,estimator
from market_flex.battery import Battery,optimise
from analyse_ml import score,BASELINES

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def acquire(zone,year,end):
    cache=ROOT/'data/raw/energy_charts';cache.mkdir(parents=True,exist_ok=True)
    path=cache/f'{zone}_{year}.json';meta=path.with_suffix('.metadata.json')
    url=f'https://api.energy-charts.info/price?bzn={zone}&start={year}-01-01&end={end}'
    if not path.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'market-flex-research/1.0'})
        with urllib.request.urlopen(req,timeout=90) as r:raw=r.read()
        path.write_bytes(raw)
        meta.write_text(json.dumps({'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'sha256':sha(path)},indent=2))
    record=json.loads(meta.read_text());assert record['sha256']==sha(path) and record['url']==url
    body=json.loads(path.read_text());assert body['unit'].replace(' ','') in ('EUR/MWh','€/MWh'),body['unit']
    idx=pd.to_datetime(body['unix_seconds'],unit='s',utc=True).rename('timestamp_utc')
    p=pd.Series(body['price'],index=idx,dtype=float)
    expected=pd.date_range(f'{year}-01-01',pd.Timestamp(end)+pd.Timedelta(days=1),freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
    assert p.index.equals(expected) and p.index.is_unique and np.isfinite(p).all(),'Coverage/resolution gate failed'
    record.update(zone=zone,year=year,hours=len(p),unit=body['unit'],license_info=body.get('license_info'))
    return p,record

def run():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--bridge-only',action='store_true');args=ap.parse_args()
    cfg=json.loads((ROOT/'config/ml-evaluation.json').read_text());sel=json.loads((ROOT/'reports/ml_selection_2024.json').read_text())
    source=ROOT/'data/processed/fundamentals_prices_2024_hourly.csv'
    assert sha(source)==json.loads((ROOT/'reports/ml_validation_2024.json').read_text())['input_sha256']
    data=pd.read_csv(source);data.timestamp_utc=pd.to_datetime(data.timestamp_utc,utc=True)
    old={z:data[data.zone==z].set_index('timestamp_utc').price_eur_mwh.sort_index() for z in cfg['zones']}
    provenance=[];bridges=[]
    for z in cfg['zones']:
        p,rec=acquire(z,2024,'2024-12-31');provenance.append(rec)
        assert p.index.equals(old[z].index)
        delta=(p-old[z]).abs();bridges.append({'zone':z,'hours':len(p),'max_absolute_difference_eur_mwh':float(delta.max()),'matched_within_tolerance':bool((delta<=.011).all())})
    (ROOT/'reports/source_bridge_2024.json').write_text(json.dumps({'sources':provenance,'comparison':bridges},indent=2))
    assert all(x['matched_within_tolerance'] for x in bridges),'Source bridge failed; do not evaluate 2025'
    print('2024 SOURCE BRIDGE PASSED',flush=True)
    if args.bridge_only:return
    metrics=[];daily=[];hourly=[];timing=[];spec=candidates(cfg);battery=Battery()
    for z in cfg['zones']:
        p,rec=acquire(z,2025,'2025-09-30');provenance.append(rec)
        parts=[]
        for day,g in p.groupby(p.index.tz_convert('Europe/Berlin').date):
            if str(day)<'2025-01-09':continue
            f,a=day_features(p,g.index);parts.append(f);timing.append({'zone':z,'day_cet':str(day),**a})
        x=pd.concat(parts);actual=p.loc[x.index];assert len(actual)==6359
        train,_=feature_matrix(old[z]);train=train.loc[mask(train.index,cfg['final_training'])]
        oracle={str(day):optimise(g,battery).net_margin_eur.sum() for day,g in actual.groupby(actual.index.tz_convert('Europe/Berlin').date)}
        for name in sel[z]['evaluation_models']+['perfect_foresight']:
            if name=='perfect_foresight':pred=actual
            elif name in BASELINES:pred=x['latest_same_hour' if name==BASELINES[0] else 'seven_day_same_hour_mean']
            else:
                model=estimator(spec[name]);model.fit(train,old[z].loc[train.index]);pred=pd.Series(model.predict(x),index=x.index)
            m,d,h=score(z,'independent_2025',name,pred,actual,battery,oracle)
            assert m['days']==265 and m['hours']==6359
            metrics.append(m);daily.append(d);hourly.append(h)
            print(z,name,round(m['net_margin_eur'],2),flush=True)
    out=ROOT/'reports';m=pd.DataFrame(metrics);d=pd.concat(daily,ignore_index=True)
    m.to_csv(out/'independent_metrics_2025.csv',index=False);d.to_csv(out/'independent_daily_2025.csv',index=False)
    d.assign(month=d.day_cet.str[:7]).groupby(['zone','model','month'])[['gross_margin_eur','degradation_eur','net_margin_eur']].sum().to_csv(out/'independent_monthly_2025.csv')
    pairs=[]
    for z,g in d.groupby('zone'):
        base=g[g.model=='seven_day_same_hour'].set_index('day_cet').net_margin_eur
        for name,s in g.groupby('model'):
            for day,value in (s.set_index('day_cet').net_margin_eur-base).items():pairs.append({'zone':z,'model':name,'day_cet':day,'net_difference_vs_seven_day_eur':value})
    pd.DataFrame(pairs).to_csv(out/'independent_paired_daily_2025.csv',index=False)
    pd.concat(hourly,ignore_index=True).to_csv(ROOT/'data/processed/independent_dispatch_2025.csv',index=False)
    pd.DataFrame(timing).to_csv(ROOT/'data/processed/independent_timing_2025.csv',index=False)
    tracked=['docs/independent-2025-protocol.md','scripts/evaluate_2025.py','config/ml-evaluation.json','reports/ml_selection_2024.json','src/market_flex/ml.py','src/market_flex/battery.py','src/market_flex/forecast.py','scripts/analyse_ml.py']
    (out/'independent_audit_2025.json').write_text(json.dumps({'sources':provenance,'bridge':bridges,'hashes':{f:sha(ROOT/f) for f in tracked},'training_input_sha256':sha(source),'evaluation_start':'2025-01-09','evaluation_end':'2025-09-30','refit_on_2025':False,'selection_changed':False,'daily_schedules':len(d),'gates':['exact hourly coverage','finite prices','2024 source bridge','fixed training input hash','forecast-time availability','unchanged settlement dispatch','oracle dominance']},indent=2))
if __name__=='__main__':run()
