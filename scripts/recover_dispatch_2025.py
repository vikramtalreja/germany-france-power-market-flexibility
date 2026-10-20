"""Recover the frozen backtest from byte-verified public sources, then reconcile.
Does not recreate missing national fundamentals or change the original experiments.
"""
from pathlib import Path
import sys,json,hashlib,time,urllib.request,urllib.error,platform,gzip
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import numpy as np
import pandas as pd
import sklearn,pyomo,highspy
from market_flex.ml import feature_matrix,day_features,mask,candidates,estimator
from market_flex.battery import Battery,optimise
from analyse_ml import score,BASELINES

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    out=ROOT/"reports"
    source_audit=json.loads((out/"independent_audit_2025.json").read_text())
    for name,expected in source_audit["hashes"].items():
        assert digest(ROOT/name)==expected, f"Frozen file changed: {name}"
    cfg=json.loads((ROOT/"config/ml-evaluation.json").read_text())
    selections=json.loads((out/"ml_selection_2024.json").read_text())
    sources={};records=[]
    cache=ROOT/"data/raw/recovered_energy_charts";cache.mkdir(parents=True,exist_ok=True)
    last_request=0.
    for record in source_audit["sources"]:
        path=cache/f'{record["zone"]}_{record["year"]}.json'
        if not path.exists():
            for attempt in range(4):
                wait=max(0,31-(time.monotonic()-last_request))
                if wait:time.sleep(wait)
                last_request=time.monotonic()
                try:
                    request=urllib.request.Request(record["url"],headers={"User-Agent":"market-flex-recovery/1.0"})
                    with urllib.request.urlopen(request,timeout=90) as response:raw=response.read()
                    path.write_bytes(raw);break
                except urllib.error.HTTPError as err:
                    if err.code!=429 or attempt==3:raise
                    delay=err.headers.get("Retry-After","60")
                    if delay.isdigit():time.sleep(int(delay)+1)
                    else:
                        from email.utils import parsedate_to_datetime
                        time.sleep(max(1,(parsedate_to_datetime(delay)-datetime.now(timezone.utc)).total_seconds()+1))
        assert digest(path)==record["sha256"], f"Source bytes changed: {record['url']}; stop rather than substitute revised data"
        body=json.loads(path.read_text())
        assert body["unit"].replace(" ","") in ("EUR/MWh","€/MWh")
        idx=pd.to_datetime(body["unix_seconds"],unit="s",utc=True).rename("timestamp_utc")
        p=pd.Series(body["price"],index=idx,dtype=float)
        year=record["year"];end="2025-01-01" if year==2024 else "2025-10-01"
        expected=pd.date_range(f"{year}-01-01",end,freq="h",inclusive="left",tz="Europe/Berlin").tz_convert("UTC")
        assert idx.equals(expected) and idx.is_unique and np.isfinite(p).all()
        sources[(record["zone"],year)]=p
        records.append({**record,"recovery_sha256":digest(path),"byte_identical":True})
        print("Verified",record["zone"],year,flush=True)
    # The earlier source bridge established exact equality of these 2024 prices to
    # the original processed price column. ML uses prices only, no fundamentals.
    assert all(r["max_absolute_difference_eur_mwh"]==0 for r in source_audit["bridge"])
    specs=candidates(cfg);bp=cfg["battery"]
    battery=Battery(bp["power_mw"],bp["energy_mwh"],bp["round_trip_efficiency"],bp["start_end_soc_fraction"],bp["degradation_eur_per_mwh_discharged"])
    reference=pd.read_csv(out/"independent_daily_2025.csv").set_index(["zone","model","day_cet"]).sort_index()
    metrics_ref=pd.read_csv(out/"independent_metrics_2025.csv").set_index(["zone","model"]).sort_index()
    hourly=[];daily=[];metrics=[]
    for zone in cfg["zones"]:
        old=sources[(zone,2024)];p=sources[(zone,2025)]
        train,_=feature_matrix(old);train=train.loc[mask(train.index,cfg["final_training"])]
        parts=[]
        for day,g in p.groupby(p.index.tz_convert("Europe/Berlin").date):
            if str(day)<"2025-01-09":continue
            f,_=day_features(p,g.index);parts.append(f)
        x=pd.concat(parts);actual=p.loc[x.index]
        oracle={str(day):optimise(g,battery).net_margin_eur.sum() for day,g in actual.groupby(actual.index.tz_convert("Europe/Berlin").date)}
        for name in selections[zone]["evaluation_models"]+["perfect_foresight"]:
            if name=="perfect_foresight":pred=actual
            elif name in BASELINES:pred=x["latest_same_hour" if name==BASELINES[0] else "seven_day_same_hour_mean"]
            else:
                model=estimator(specs[name]);model.fit(train,old.loc[train.index]);pred=pd.Series(model.predict(x),index=x.index)
            m,d,h=score(zone,"independent_2025",name,pred,actual,battery,oracle)
            daily.append(d);hourly.append(h);metrics.append(m)
            print(zone,name,m["net_margin_eur"],flush=True)
    d=pd.concat(daily).set_index(["zone","model","day_cet"]).sort_index()
    assert d.index.equals(reference.index)
    checks={}
    for col in ["hours","gross_margin_eur","degradation_eur","net_margin_eur","oracle_gap_eur","discharged_mwh"]:
        error=float((d[col]-reference[col]).abs().max());checks[col]=error
        np.testing.assert_allclose(d[col],reference[col],rtol=0,atol=1e-5,err_msg=col)
    m=pd.DataFrame(metrics).set_index(["zone","model"]).sort_index()
    for col in ["mae_eur_mwh","rmse_eur_mwh","net_margin_eur","loss_days"]:
        np.testing.assert_allclose(m[col],metrics_ref[col],rtol=0,atol=1e-4,err_msg=col)
    processed=ROOT/"data/processed";processed.mkdir(parents=True,exist_ok=True)
    dispatch=pd.concat(hourly,ignore_index=True)
    dispatch.to_csv(processed/"independent_dispatch_2025.csv",index=False)
    permanent=ROOT/"data/recovered";permanent.mkdir(parents=True,exist_ok=True)
    # Also keep the full CSV in GitHub, independent of expiring workflow artifacts.
    dispatch.to_csv(permanent/"independent_dispatch_2025.csv.gz",index=False,compression={"method":"gzip","mtime":0})
    for (zone,year),prices in sources.items():
        prices.rename("price_eur_mwh").to_csv(permanent/f"prices_{zone}_{year}.csv.gz",compression={"method":"gzip","mtime":0})
    (out/"dispatch_recovery_2025.json").write_text(json.dumps({
        "status":"reconstructed_and_reconciled","utc":datetime.now(timezone.utc).isoformat(),
        "sources":records,"rows":len(dispatch),"daily_max_abs_errors":checks,
        "hourly_original_hash_unavailable":True,
        "qualification":"Reconstructed schedules match original daily and aggregate results within declared tolerance; original hourly bytes were not retained, so identical hourly tie-breaking is not established.",
        "versions":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__,"pyomo":pyomo.__version__,"highs":highspy.Highs().version()},
        "dispatch_sha256":digest(processed/"independent_dispatch_2025.csv"),
        "script_sha256":digest(Path(__file__))
    },indent=2))
    print("RECOVERY RECONCILED",flush=True)

if __name__=="__main__":run()
