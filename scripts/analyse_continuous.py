"""Execute the frozen continuous-operation retrospective comparison."""
from pathlib import Path
import sys,json,hashlib,platform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
import numpy as np
import pandas as pd
import pyomo,highspy
from market_flex.battery import Battery,optimise
from market_flex.forecast import forecast
from market_flex.continuous import optimise_horizon,rolling_run,settle_committed,validate

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    config=ROOT/"config/continuous-operation.json";cfg=json.loads(config.read_text())
    out=ROOT/"reports";storage=ROOT/"data/continuous";storage.mkdir(parents=True,exist_ok=True)
    battery=Battery(**cfg["battery"])
    start,end=cfg["evaluation"]["start"],cfg["evaluation"]["end"]
    original=pd.read_csv(out/"independent_daily_2025.csv")
    all_hourly=[];all_daily=[];all_decisions=[];metrics=[];inputs={};oracles={}
    def record(zone,policy,fee,h):
        h=h.copy();h.index.name="timestamp_utc"
        h["zone"]=zone;h["policy"]=policy;h["fee_eur_per_mwh_each_side"]=fee
        h["day_cet"]=h.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d")
        daily=h.groupby("day_cet").agg(net_margin_eur=("net_margin_eur","sum"),gross_margin_eur=("gross_margin_eur","sum"),degradation_eur=("degradation_eur","sum"),transaction_cost_eur=("transaction_cost_eur","sum"),discharged_mwh=("discharge_mw","sum"),start_soc_mwh=("soc_start_mwh","first"),end_soc_mwh=("soc_end_mwh","last"))
        daily["zone"]=zone;daily["policy"]=policy;daily["fee_eur_per_mwh_each_side"]=fee
        all_daily.append(daily.reset_index());all_hourly.append(h.reset_index())
        metrics.append({"zone":zone,"policy":policy,"fee_eur_per_mwh_each_side":fee,"hours":len(h),"days":len(daily),"net_margin_eur":h.net_margin_eur.sum(),"gross_margin_eur":h.gross_margin_eur.sum(),"degradation_eur":h.degradation_eur.sum(),"transaction_cost_eur":h.transaction_cost_eur.sum(),"discharged_mwh":h.discharge_mw.sum(),"loss_days":int((daily.net_margin_eur< -1e-6).sum()),"worst_day_eur":daily.net_margin_eur.min(),"boundary_days_away_from_50pct":int((abs(daily.end_soc_mwh.iloc[:-1]-1)>1e-6).sum())})
        print(zone,policy,round(h.net_margin_eur.sum(),2),flush=True)
        return daily
    for zone in cfg["zones"]:
        path=ROOT/f"data/recovered/prices_{zone}_2025.csv.gz";inputs[str(path.relative_to(ROOT))]=sha(path)
        p=pd.read_csv(path);p.timestamp_utc=pd.to_datetime(p.timestamp_utc,utc=True)
        prices=p.set_index("timestamp_utc").price_eur_mwh
        idx=pd.date_range(start,pd.Timestamp(end)+pd.Timedelta(days=1),freq="h",inclusive="left",tz="Europe/Berlin").tz_convert("UTC")
        actual=prices.loc[idx];assert len(actual)==6359 and np.isfinite(actual).all()
        for fee in (0,1):
            # Global perfect foresight is a bound under the same initial/final inventory.
            oracle=optimise_horizon(actual,1,1,battery,fee,cfg["solver"]["time_limit_seconds"])
            oracle=settle_committed(oracle,actual,"perfect_foresight_only")
            record(zone,f"global_oracle_fee_{fee}",fee,oracle)
            oracles[(zone,fee)]=float(oracle.net_margin_eur.sum())
            blocks=[]
            for day,g in actual.groupby(actual.index.tz_convert("Europe/Berlin").date):
                pred,audit=forecast(prices,g.index,"seven_day_same_hour")
                if fee==0:
                    legacy=optimise(pred,battery)
                    schedule=legacy.rename(columns={"price_eur_mwh":"forecast_eur_mwh","net_margin_eur":"forecast_net_margin_eur"}).drop(columns="gross_margin_eur")
                    schedule["dt_hours"]=1.;schedule["transaction_cost_eur"]=0.
                else:schedule=optimise_horizon(pred,1,1,battery,fee)
                blocks.append(settle_committed(schedule,g,pd.Timestamp(audit["decision_cutoff_utc"])))
            h=pd.concat(blocks);validate(h,battery,1,1)
            daily=record(zone,f"daily_reset_fee_{fee}",fee,h)
            if fee==0:
                ref=original[(original.zone==zone)&(original.model=="seven_day_same_hour")].set_index("day_cet").sort_index()
                assert daily.index.equals(ref.index)
                for col in ["net_margin_eur","gross_margin_eur","degradation_eur","discharged_mwh"]:
                    np.testing.assert_allclose(daily[col],ref[col],atol=1e-5,rtol=0)
        for scenario in cfg["scenarios"]:
            h,a=rolling_run(prices,start,end,scenario["terminal_fraction"],scenario["fee_eur_per_mwh_each_side"],battery)
            fee=scenario["fee_eur_per_mwh_each_side"];policy=scenario["name"]
            assert h.net_margin_eur.sum()<=oracles[(zone,fee)]+1e-4
            a["zone"]=zone;a["policy"]=policy;all_decisions.append(a)
            record(zone,policy,fee,h)
    m=pd.DataFrame(metrics)
    for r in m.itertuples():
        assert r.net_margin_eur<=oracles[(r.zone,int(r.fee_eur_per_mwh_each_side))]+1e-4
    m["oracle_gap_eur"]=[oracles[(r.zone,int(r.fee_eur_per_mwh_each_side))]-r.net_margin_eur for r in m.itertuples()]
    m.to_csv(out/"continuous_metrics_2025.csv",index=False)
    d=pd.concat(all_daily,ignore_index=True);d.to_csv(out/"continuous_daily_2025.csv",index=False)
    d.assign(month=d.day_cet.str[:7]).groupby(["zone","policy","month"])[["net_margin_eur","gross_margin_eur","transaction_cost_eur","degradation_eur"]].sum().to_csv(out/"continuous_monthly_2025.csv")
    pd.concat(all_decisions,ignore_index=True).to_csv(out/"continuous_decisions_2025.csv",index=False)
    full=pd.concat(all_hourly,ignore_index=True)
    full.to_csv(storage/"dispatch_2025.csv.gz",index=False,compression={"method":"gzip","mtime":0})
    ledger=full[~full.policy.str.startswith("global_oracle")][["zone","policy","timestamp_utc","day_cet","decision_cutoff_utc","signed_da_position_mwh","forecast_eur_mwh","actual_eur_mwh","sales_eur","purchase_eur","gross_margin_eur","transaction_cost_eur"]].copy()
    assert not ledger.duplicated(["zone","policy","timestamp_utc"]).any()
    np.testing.assert_allclose(ledger.actual_eur_mwh*ledger.signed_da_position_mwh,ledger.gross_margin_eur,atol=1e-6,rtol=0)
    ledger.to_csv(storage/"trade_ledger_2025.csv.gz",index=False,compression={"method":"gzip","mtime":0})
    versions={"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"pyomo":pyomo.__version__,"highs":highspy.Highs().version()}
    audit={"status":"completed","retrospective":True,"config_sha256":sha(config),"inputs_sha256":inputs,"code_sha256":{f:sha(ROOT/f) for f in ["src/market_flex/continuous.py","scripts/analyse_continuous.py","tests/test_continuous.py"]},"versions":versions,"checks":["original zero-fee daily results reconciled","SOC continuity through all boundaries","prior commitments preserved","forecast availability at fixed issuance cutoff","fixed initial and final SOC","no simultaneous charge/discharge","signed ledger cashflow reconciled","all policies below same-fee global oracle"],"scored_hours":len(full),"scored_daily_rows":len(d)}
    (out/"continuous_audit_2025.json").write_text(json.dumps(audit,indent=2))
    from report_continuous import write_report
    write_report(m,d,full)
if __name__=="__main__":run()
