"""Execute the predeclared version-1 ML protocol without evaluation retuning."""
from pathlib import Path
import sys,json,hashlib,platform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pandas as pd
import sklearn,pyomo,highspy
from market_flex.ml import feature_matrix,mask,candidates,estimator,select,assert_training_boundary,NUMERIC,WEEKDAYS
from market_flex.battery import Battery,optimise
from market_flex.forecast import settle
BASELINES=['latest_same_hour','seven_day_same_hour']

def score(zone,stage,name,pred,actual,battery,oracle_daily):
    daily=[];hourly=[]
    assert pred.index.equals(actual.index) and pred.index.is_unique and np.isfinite(pred).all()
    for date,g in actual.groupby(actual.index.tz_convert('Europe/Berlin').date):
        schedule=optimise(pred.loc[g.index],battery);s=settle(schedule,g)
        assert all(s[c].equals(schedule[c]) for c in ['charge_mw','discharge_mw','soc_start_mwh','soc_end_mwh'])
        net=s.net_margin_eur.sum();gap=oracle_daily[str(date)]-net
        assert gap>=-1e-5
        daily.append(dict(zone=zone,stage=stage,model=name,day_cet=str(date),hours=len(g),gross_margin_eur=s.gross_margin_eur.sum(),degradation_eur=s.degradation_eur.sum(),net_margin_eur=net,oracle_gap_eur=gap,discharged_mwh=s.discharge_mw.sum()))
        s['zone']=zone;s['stage']=stage;s['model']=name;s['day_cet']=str(date);hourly.append(s.reset_index())
    d=pd.DataFrame(daily);h=pd.concat(hourly,ignore_index=True);err=pred-actual
    metrics=dict(zone=zone,stage=stage,model=name,hours=len(actual),days=len(d),mae_eur_mwh=float(err.abs().mean()),rmse_eur_mwh=float(np.sqrt((err**2).mean())),gross_margin_eur=d.gross_margin_eur.sum(),degradation_eur=d.degradation_eur.sum(),net_margin_eur=d.net_margin_eur.sum(),oracle_gap_eur=d.oracle_gap_eur.sum(),discharged_mwh=d.discharged_mwh.sum(),loss_days=int((d.net_margin_eur<-1e-6).sum()),worst_day_eur=d.net_margin_eur.min())
    for label,a,p in [('spike',actual>200,pred>200),('negative',actual<0,pred<0)]:
        tp=int((a&p).sum());metrics.update({label+'_actual_hours':int(a.sum()),label+'_predicted_hours':int(p.sum()),label+'_precision':tp/int(p.sum()) if p.sum() else np.nan,label+'_recall':tp/int(a.sum()) if a.sum() else np.nan})
    return metrics,d,h

def run():
    config_path=ROOT/'config/ml-evaluation.json';config=json.loads(config_path.read_text())
    source=ROOT/'data/processed/fundamentals_prices_2024_hourly.csv'
    data=pd.read_csv(source);data.timestamp_utc=pd.to_datetime(data.timestamp_utc,utc=True)
    out=ROOT/'reports';processed=ROOT/'data/processed';specs=candidates(config);order=BASELINES+list(specs)
    bp=config['battery'];battery=Battery(bp['power_mw'],bp['energy_mwh'],bp['round_trip_efficiency'],bp['start_end_soc_fraction'],bp['degradation_eur_per_mwh_discharged'])
    all_metrics=[];all_daily=[];all_hourly=[];selections={};audits=[];fitted_audit=[];prepared={}
    expected=pd.date_range('2024-01-01','2025-01-01',freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
    # Complete validation and save both zones' choices before any evaluation scoring.
    for zone in config['zones']:
        p=data[data.zone==zone].set_index('timestamp_utc').price_eur_mwh.sort_index();assert p.index.equals(expected)
        x,a=feature_matrix(p);a['zone']=zone;audits.append(a)
        train=x.loc[mask(x.index,config['initial_training'])];val=x.loc[mask(x.index,config['validation'])]
        assert_training_boundary(train.index,config['validation']['start'])
        actual=p.loc[val.index];oracle={}
        for day,g in actual.groupby(actual.index.tz_convert('Europe/Berlin').date):oracle[str(day)]=optimise(g,battery).net_margin_eur.sum()
        rows=[]
        for name in order:
            if name in BASELINES:pred=val['latest_same_hour' if name==BASELINES[0] else 'seven_day_same_hour_mean']
            else:
                model=estimator(specs[name]);model.fit(train,p.loc[train.index]);pred=pd.Series(model.predict(val),index=val.index)
                fitted_audit.append(dict(zone=zone,stage='initial_training',model=name,rows=len(train),first_target=str(train.index[0]),last_target=str(train.index[-1])))
            m,d,h=score(zone,'validation',name,pred,actual,battery,oracle);rows.append(m);all_metrics.append(m);all_daily.append(d);all_hourly.append(h)
            print(zone,'validation',name,round(m['net_margin_eur'],2),flush=True)
        summary=pd.DataFrame(rows)
        winner=select(summary,order,config['selection']['near_tie_eur'])
        mae_winner=summary.assign(order=summary.model.map({m:i for i,m in enumerate(order)})).sort_values(['mae_eur_mwh','order']).iloc[0].model
        families={f:select(summary[summary.model.isin([n for n,s in specs.items() if s['family']==f])],order) for f in ['ridge','random_forest']}
        selections[zone]={'operational':winner,'mae_winner':mae_winner,'family_winners':families,'evaluation_models':list(dict.fromkeys(BASELINES+list(families.values())+[winner,mae_winner]))}
        prepared[zone]=(p,x)
    selection_path=out/'ml_selection_2024.json';selection_path.write_text(json.dumps(selections,indent=2));selection_hash=hashlib.sha256(selection_path.read_bytes()).hexdigest()
    print('SELECTIONS FROZEN',json.dumps(selections),flush=True)
    for zone,(p,x) in prepared.items():
        train=x.loc[mask(x.index,config['final_training'])];test=x.loc[mask(x.index,config['evaluation'])]
        assert_training_boundary(train.index,config['evaluation']['start']);actual=p.loc[test.index];oracle={}
        for day,g in actual.groupby(actual.index.tz_convert('Europe/Berlin').date):oracle[str(day)]=optimise(g,battery).net_margin_eur.sum()
        for name in selections[zone]['evaluation_models']+['perfect_foresight']:
            if name=='perfect_foresight':pred=actual
            elif name in BASELINES:pred=test['latest_same_hour' if name==BASELINES[0] else 'seven_day_same_hour_mean']
            else:
                model=estimator(specs[name]);model.fit(train,p.loc[train.index]);pred=pd.Series(model.predict(test),index=test.index)
                fitted_audit.append(dict(zone=zone,stage='final_training',model=name,rows=len(train),first_target=str(train.index[0]),last_target=str(train.index[-1])))
                if specs[name]['family']=='ridge':
                    scaler=model.named_steps['features'].named_transformers_['numeric'];np.testing.assert_allclose(scaler.mean_,train[NUMERIC].mean(),atol=1e-10)
            m,d,h=score(zone,'evaluation',name,pred,actual,battery,oracle);all_metrics.append(m);all_daily.append(d);all_hourly.append(h)
            assert m['days']==122 and m['hours']==2929
            print(zone,'evaluation',name,round(m['net_margin_eur'],2),flush=True)
    assert hashlib.sha256(selection_path.read_bytes()).hexdigest()==selection_hash
    metrics=pd.DataFrame(all_metrics);daily=pd.concat(all_daily,ignore_index=True);hourly=pd.concat(all_hourly,ignore_index=True)
    metrics.to_csv(out/'ml_metrics_2024.csv',index=False);daily.to_csv(out/'ml_daily_2024.csv',index=False)
    hourly.to_csv(processed/'ml_dispatch_2024.csv',index=False);pd.concat(audits).to_csv(processed/'ml_feature_timing_2024.csv',index=False)
    pd.DataFrame(fitted_audit).to_csv(out/'ml_fit_audit_2024.csv',index=False)
    daily['month']=daily.day_cet.str[:7]
    daily.groupby(['zone','stage','model','month'])[['gross_margin_eur','degradation_eur','net_margin_eur','discharged_mwh']].sum().to_csv(out/'ml_monthly_2024.csv')
    paired=[]
    for z in config['zones']:
        sub=daily[(daily.zone==z)&(daily.stage=='evaluation')];base=sub[sub.model==BASELINES[1]].set_index('day_cet').net_margin_eur
        for name,g in sub.groupby('model'):
            delta=g.set_index('day_cet').net_margin_eur-base
            for date,value in delta.items():paired.append(dict(zone=z,model=name,day_cet=date,net_difference_vs_seven_day_eur=value))
    pd.DataFrame(paired).to_csv(out/'ml_paired_daily_2024.csv',index=False)
    audit={'protocol_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'selection_sha256_before_evaluation':selection_hash,'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'pyomo':pyomo.__version__,'highs':highspy.Highs().version()},'candidate_parameters':specs,'numeric_features':NUMERIC,'weekday_columns':WEEKDAYS,'checks':{'source_hourly_coverage':True,'training_boundaries':True,'preprocessing_fit_training_only':True,'oracle_dominance':True,'settlement_unchanged':True,'selections_unchanged_during_evaluation':True},'deviations':[],'clarifications':['JSON max_features=1 is explicitly cast to float 1.0 to implement protocol all-feature semantics, not integer one-feature semantics.'],'previously_inspected_evaluation':True,'total_scored_daily_schedules':len(daily)}
    (out/'ml_validation_2024.json').write_text(json.dumps(audit,indent=2))
    from report_ml import write_report
    write_report(metrics,daily,selections)
    return metrics
if __name__=='__main__':run()
