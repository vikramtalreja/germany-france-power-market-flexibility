"""Hourly rolling planning with preserved day-ahead commitments and continuous SOC."""
from datetime import timedelta
import math
import numpy as np
import pandas as pd
import pyomo.environ as pyo
from market_flex.battery import Battery

def check_index(index):
    if not isinstance(index,pd.DatetimeIndex) or index.tz is None or not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError("Need unique increasing timezone-aware interval starts")
    if len(index)>1 and not (np.diff(index.asi8)==3600*10**9).all():
        raise ValueError("Only contiguous hourly intervals are supported")

def issued_forecast(prices,target):
    check_index(prices.index);check_index(target)
    first=target.tz_convert("Europe/Berlin")[0].date()
    cutoff=pd.Timestamp(str(first-timedelta(days=1))+" 09:00",tz="Europe/Berlin").tz_convert("UTC")
    start=pd.Timestamp(first-timedelta(days=8),tz="Europe/Berlin").tz_convert("UTC")
    end=pd.Timestamp(first-timedelta(days=1),tz="Europe/Berlin").tz_convert("UTC")
    history=prices[(prices.index>=start)&(prices.index<end)]
    expected=pd.date_range(start,end,freq="h",inclusive="left")
    if not history.index.equals(expected) or not np.isfinite(history).all():raise ValueError("Incomplete issuance history")
    assert (history.index+pd.Timedelta(hours=1)<=cutoff).all()
    local=history.index.tz_convert("Europe/Berlin")
    frame=pd.DataFrame({"value":history.to_numpy(),"date":local.date,"hour":local.hour})
    profile=frame.groupby(["date","hour"]).value.mean().groupby("hour").mean()
    pred=pd.Series(profile.reindex(target.tz_convert("Europe/Berlin").hour).to_numpy(),index=target,name="forecast_eur_mwh")
    assert np.isfinite(pred).all()
    return pred,cutoff,end

def validate(schedule,battery,initial,terminal=None):
    tol=1e-6;eta=math.sqrt(battery.round_trip_efficiency)
    c=schedule.charge_mw;d=schedule.discharge_mw
    assert c.min()>=-tol and d.min()>=-tol
    assert c.max()<=battery.power_mw+tol and d.max()<=battery.power_mw+tol
    assert (c*d).abs().max()<tol
    soc=schedule[["soc_start_mwh","soc_end_mwh"]].to_numpy()
    assert soc.min()>=-tol and soc.max()<=battery.energy_mwh+tol
    np.testing.assert_allclose(schedule.soc_end_mwh,schedule.soc_start_mwh+eta*c*schedule.dt_hours-d*schedule.dt_hours/eta,atol=tol,rtol=0)
    np.testing.assert_allclose(schedule.soc_start_mwh.iloc[1:],schedule.soc_end_mwh.iloc[:-1],atol=tol,rtol=0)
    assert abs(schedule.soc_start_mwh.iloc[0]-initial)<tol
    if terminal is not None:assert abs(schedule.soc_end_mwh.iloc[-1]-terminal)<tol

def optimise_horizon(prices,initial,terminal,battery=Battery(),fee=0,time_limit=180):
    battery.validate();check_index(prices.index)
    assert len(prices) and np.isfinite(prices).all() and fee>=0
    assert 0<=initial<=battery.energy_mwh and 0<=terminal<=battery.energy_mwh
    n=len(prices);eta=math.sqrt(battery.round_trip_efficiency)
    m=pyo.ConcreteModel();m.t=pyo.RangeSet(0,n-1);m.k=pyo.RangeSet(0,n)
    m.c=pyo.Var(m.t,bounds=(0,battery.power_mw));m.d=pyo.Var(m.t,bounds=(0,battery.power_mw))
    m.s=pyo.Var(m.k,bounds=(0,battery.energy_mwh));m.mode=pyo.Var(m.t,within=pyo.Binary)
    m.start=pyo.Constraint(expr=m.s[0]==initial);m.end=pyo.Constraint(expr=m.s[n]==terminal)
    m.balance=pyo.Constraint(m.t,rule=lambda m,t:m.s[t+1]==m.s[t]+eta*m.c[t]-m.d[t]/eta)
    m.cm=pyo.Constraint(m.t,rule=lambda m,t:m.c[t]<=battery.power_mw*m.mode[t])
    m.dm=pyo.Constraint(m.t,rule=lambda m,t:m.d[t]<=battery.power_mw*(1-m.mode[t]))
    m.obj=pyo.Objective(expr=sum(float(prices.iloc[t])*(m.d[t]-m.c[t])-battery.degradation_eur_per_mwh_discharged*m.d[t]-fee*(m.c[t]+m.d[t]) for t in m.t),sense=pyo.maximize)
    solver=pyo.SolverFactory("highs");solver.options["mip_rel_gap"]=1e-8;solver.options["time_limit"]=time_limit
    result=solver.solve(m)
    if not pyo.check_optimal_termination(result):raise RuntimeError("Optimum not established: "+str(result.solver))
    out=pd.DataFrame({"forecast_eur_mwh":prices,"charge_mw":[pyo.value(m.c[t]) for t in m.t],"discharge_mw":[pyo.value(m.d[t]) for t in m.t],"soc_start_mwh":[pyo.value(m.s[t]) for t in m.t],"soc_end_mwh":[pyo.value(m.s[t+1]) for t in m.t]},index=prices.index)
    out.index.name="timestamp_utc";out["dt_hours"]=1.
    out["degradation_eur"]=battery.degradation_eur_per_mwh_discharged*out.discharge_mw
    out["transaction_cost_eur"]=fee*(out.charge_mw+out.discharge_mw)
    out["forecast_net_margin_eur"]=prices*(out.discharge_mw-out.charge_mw)-out.degradation_eur-out.transaction_cost_eur
    validate(out,battery,initial,terminal)
    return out

def projected_opening(previous,cutoff,initial=1.):
    if previous is None:return initial,initial,0.
    remaining=previous.loc[previous.index>=cutoff]
    if len(remaining)==0 or remaining.index[0]!=cutoff:raise ValueError("Prior committed schedule does not cover the cutoff")
    at_cutoff=float(remaining.soc_start_mwh.iloc[0])
    change=float((remaining.soc_end_mwh-remaining.soc_start_mwh).sum())
    opening=at_cutoff+change
    assert abs(opening-previous.soc_end_mwh.iloc[-1])<1e-6
    return opening,at_cutoff,change

def settle_committed(schedule,actual,cutoff):
    assert schedule.index.equals(actual.index) and np.isfinite(actual).all()
    out=schedule.copy()
    # Quantities already committed; actual prices only enter financial settlement.
    out["decision_cutoff_utc"]=str(cutoff)
    out["signed_da_position_mwh"]=(out.discharge_mw-out.charge_mw)*out.dt_hours
    out["actual_eur_mwh"]=actual
    out["sales_eur"]=actual*out.discharge_mw*out.dt_hours
    out["purchase_eur"]=actual*out.charge_mw*out.dt_hours
    out["gross_margin_eur"]=out.sales_eur-out.purchase_eur
    out["net_margin_eur"]=out.gross_margin_eur-out.degradation_eur-out.transaction_cost_eur
    np.testing.assert_allclose(out.gross_margin_eur,actual*out.signed_da_position_mwh,atol=1e-6,rtol=0)
    return out

def rolling_run(prices,start,end,terminal_fraction=.5,fee=0,battery=Battery()):
    target=prices.loc[(prices.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d")>=start)&(prices.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d")<=end)]
    expected=pd.date_range(start,pd.Timestamp(end)+pd.Timedelta(days=1),freq="h",inclusive="left",tz="Europe/Berlin").tz_convert("UTC")
    assert target.index.equals(expected)
    blocks=[];decisions=[];previous=None
    groups=list(target.groupby(target.index.tz_convert("Europe/Berlin").date))
    for i,(day,g) in enumerate(groups):
        horizon=g.index if i==len(groups)-1 else g.index.append(groups[i+1][1].index)
        pred,cutoff,history_end=issued_forecast(prices,horizon)
        before=previous.copy(deep=True) if previous is not None else None
        initial,at_cutoff,change=projected_opening(previous,cutoff,battery.initial_fraction*battery.energy_mwh)
        # Clip only sub-tolerance solver boundary noise.
        if -1e-6<=initial<=0:initial=0.
        if battery.energy_mwh<=initial<=battery.energy_mwh+1e-6:initial=battery.energy_mwh
        terminal=battery.initial_fraction*battery.energy_mwh if i==len(groups)-1 else terminal_fraction*battery.energy_mwh
        plan=optimise_horizon(pred,initial,terminal,battery,fee)
        committed=plan.loc[g.index].copy()
        if previous is not None:pd.testing.assert_frame_equal(previous,before)
        decisions.append({"day_cet":str(day),"decision_cutoff_utc":str(cutoff),"history_end_exclusive_utc":str(history_end),"soc_at_cutoff_mwh":at_cutoff,"remaining_committed_soc_change_mwh":change,"projected_delivery_start_soc_mwh":initial,"committed_delivery_end_soc_mwh":committed.soc_end_mwh.iloc[-1],"planning_terminal_soc_mwh":terminal,"planning_hours":len(horizon),"committed_hours":len(g),"provisional_hours":len(horizon)-len(g)})
        # Retain physical commitments independently of settlement data.
        previous=committed.copy(deep=True)
        settled=settle_committed(committed,g,cutoff);settled["day_cet"]=str(day);blocks.append(settled)
    combined=pd.concat(blocks);validate(combined,battery,battery.initial_fraction*battery.energy_mwh,battery.initial_fraction*battery.energy_mwh)
    assert combined.index.is_unique
    return combined,pd.DataFrame(decisions)
