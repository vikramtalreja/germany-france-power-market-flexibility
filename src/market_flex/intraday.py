"""One pre-delivery intraday auction adjustment; DA trades are immutable.

Forecast-only planning and separate clearing-price settlement. This is an
idealised full-fill, price-taking model, not a continuous order-book simulator.
"""
import math
import numpy as np
import pandas as pd
import pyomo.environ as pyo
from market_flex.battery import Battery
from market_flex.continuous import validate


def _utc(value):
    t=pd.Timestamp(value)
    if t.tz is None: raise ValueError('Timestamp must include timezone')
    return t.tz_convert('UTC')


def _check_frame(da):
    required=['dt_hours','signed_da_position_mwh','actual_eur_mwh','soc_start_mwh',
              'soc_end_mwh','charge_mw','discharge_mw']
    if not all(c in da for c in required): raise ValueError('Missing DA columns')
    i=da.index
    if not isinstance(i,pd.DatetimeIndex) or i.tz is None or not i.is_unique or not i.is_monotonic_increasing:
        raise ValueError('Unique increasing timezone-aware delivery starts required')
    if not len(da) or not np.isfinite(da[required].to_numpy()).all(): raise ValueError('Empty/nonfinite DA input')
    if not np.isin(da.dt_hours,[.25,.5,1.]).all(): raise ValueError('Unsupported duration')
    ends=i+pd.to_timedelta(da.dt_hours.to_numpy(),unit='h')
    if len(da)>1 and not ends[:-1].equals(i[1:]): raise ValueError('Noncontiguous delivery intervals')
    np.testing.assert_allclose(da.signed_da_position_mwh,(da.discharge_mw-da.charge_mw)*da.dt_hours,atol=1e-6,rtol=0)


def plan_adjustment(da,forecast,forecast_issued_at,decision_at,gate_closure_at,
                    max_buy_mwh,max_sell_mwh,fee=1.,battery=Battery()):
    """Return revised physical dispatch and incremental ID quantities.

    The window must be entirely in the future and the original DA start/end
    energy is preserved, leaving commitments outside the window feasible.
    Volumes are declared executable bounds, not inferred from market totals.
    """
    battery.validate();_check_frame(da)
    issued,decision,gate=map(_utc,[forecast_issued_at,decision_at,gate_closure_at])
    if not issued<=decision<gate<=da.index[0]: raise ValueError('Invalid information/trading timeline')
    if not forecast.index.equals(da.index) or not np.isfinite(forecast).all(): raise ValueError('Invalid forecast')
    if not np.isfinite(fee) or fee<0: raise ValueError('Invalid fee')
    n=len(da)
    buy=np.broadcast_to(np.asarray(max_buy_mwh,dtype=float),(n,)).copy()
    sell=np.broadcast_to(np.asarray(max_sell_mwh,dtype=float),(n,)).copy()
    if not np.isfinite(buy).all() or not np.isfinite(sell).all() or min(buy.min(),sell.min())<0:
        raise ValueError('Invalid executable volume bounds')
    initial=float(da.soc_start_mwh.iloc[0]);terminal=float(da.soc_end_mwh.iloc[-1])
    validate(da,battery,initial,terminal)
    m=pyo.ConcreteModel();m.t=pyo.RangeSet(0,n-1);m.k=pyo.RangeSet(0,n)
    m.c=pyo.Var(m.t,bounds=(0,battery.power_mw));m.d=pyo.Var(m.t,bounds=(0,battery.power_mw))
    m.s=pyo.Var(m.k,bounds=(0,battery.energy_mwh));m.mode=pyo.Var(m.t,within=pyo.Binary)
    m.b=pyo.Var(m.t,within=pyo.NonNegativeReals);m.v=pyo.Var(m.t,within=pyo.NonNegativeReals)
    m.trade_mode=pyo.Var(m.t,within=pyo.Binary)
    m.start=pyo.Constraint(expr=m.s[0]==initial);m.end=pyo.Constraint(expr=m.s[n]==terminal)
    eta=math.sqrt(battery.round_trip_efficiency)
    m.energy=pyo.Constraint(m.t,rule=lambda m,t:m.s[t+1]==m.s[t]+float(da.dt_hours.iloc[t])*(eta*m.c[t]-m.d[t]/eta))
    m.cm=pyo.Constraint(m.t,rule=lambda m,t:m.c[t]<=battery.power_mw*m.mode[t])
    m.dm=pyo.Constraint(m.t,rule=lambda m,t:m.d[t]<=battery.power_mw*(1-m.mode[t]))
    m.bm=pyo.Constraint(m.t,rule=lambda m,t:m.b[t]<=float(buy[t])*m.trade_mode[t])
    m.vm=pyo.Constraint(m.t,rule=lambda m,t:m.v[t]<=float(sell[t])*(1-m.trade_mode[t]))
    m.position=pyo.Constraint(m.t,rule=lambda m,t:(m.d[t]-m.c[t])*float(da.dt_hours.iloc[t])==float(da.signed_da_position_mwh.iloc[t])+m.v[t]-m.b[t])
    # Original DA proceeds are fixed: they do NOT reprice the revised dispatch.
    m.obj=pyo.Objective(expr=sum(float(forecast.iloc[t])*(m.v[t]-m.b[t])-fee*(m.v[t]+m.b[t])-battery.degradation_eur_per_mwh_discharged*m.d[t]*float(da.dt_hours.iloc[t]) for t in m.t),sense=pyo.maximize)
    solver=pyo.SolverFactory('highs');solver.options['mip_rel_gap']=1e-8
    result=solver.solve(m)
    if not pyo.check_optimal_termination(result): raise RuntimeError('Intraday optimum not established')
    out=pd.DataFrame(index=da.index)
    for name,var in [('charge_mw',m.c),('discharge_mw',m.d),('id_buy_mwh',m.b),('id_sell_mwh',m.v)]:
        out[name]=[pyo.value(var[t]) for t in m.t]
    out['soc_start_mwh']=[pyo.value(m.s[t]) for t in m.t]
    out['soc_end_mwh']=[pyo.value(m.s[t+1]) for t in m.t]
    out['dt_hours']=da.dt_hours;out['forecast_eur_mwh']=forecast
    out['signed_id_position_mwh']=out.id_sell_mwh-out.id_buy_mwh
    out['id_fee_eur']=fee*(out.id_sell_mwh+out.id_buy_mwh)
    out['degradation_eur']=battery.degradation_eur_per_mwh_discharged*out.discharge_mw*out.dt_hours
    out['decision_at_utc']=str(decision);out['forecast_issued_at_utc']=str(issued)
    out['gate_closure_at_utc']=str(gate)
    validate(out,battery,initial,terminal)
    np.testing.assert_allclose((out.discharge_mw-out.charge_mw)*out.dt_hours,da.signed_da_position_mwh+out.signed_id_position_mwh,atol=1e-6,rtol=0)
    return out


def settle_adjustment(da,plan,clearing_prices,battery=Battery()):
    """Keep original trades; append ID trades and account for revised physics."""
    _check_frame(da)
    if not da.index.equals(plan.index) or not da.index.equals(clearing_prices.index) or not np.isfinite(clearing_prices).all():
        raise ValueError('Settlement intervals/prices invalid')
    validate(plan,battery,float(da.soc_start_mwh.iloc[0]),float(da.soc_end_mwh.iloc[-1]))
    np.testing.assert_allclose((plan.discharge_mw-plan.charge_mw)*plan.dt_hours,da.signed_da_position_mwh+plan.signed_id_position_mwh,atol=1e-6,rtol=0)
    out=plan.copy();out['actual_id_eur_mwh']=clearing_prices
    out['da_cashflow_eur']=da.signed_da_position_mwh*da.actual_eur_mwh
    out['id_cashflow_eur']=plan.signed_id_position_mwh*clearing_prices
    da_fee=da.transaction_cost_eur if 'transaction_cost_eur' in da else pd.Series(0.,index=da.index)
    old_wear=battery.degradation_eur_per_mwh_discharged*da.discharge_mw*da.dt_hours
    out['da_fee_eur']=da_fee
    out['net_margin_eur']=out.da_cashflow_eur+out.id_cashflow_eur-da_fee-out.id_fee_eur-out.degradation_eur
    out['original_da_net_margin_eur']=out.da_cashflow_eur-da_fee-old_wear
    out['incremental_margin_eur']=out.net_margin_eur-out.original_da_net_margin_eur
    # Exact zero residual imbalance under the perfect-fill/execution assumption.
    out['imbalance_mwh']=(out.discharge_mw-out.charge_mw)*out.dt_hours-da.signed_da_position_mwh-plan.signed_id_position_mwh
    rows=[]
    for market,qty,price,fee in [('DA',da.signed_da_position_mwh,da.actual_eur_mwh,da_fee),
                              ('ID',plan.signed_id_position_mwh,clearing_prices,plan.id_fee_eur)]:
        rows.append(pd.DataFrame({'timestamp_utc':da.index,'market':market,'signed_position_mwh':qty.to_numpy(),
                                 'price_eur_mwh':price.to_numpy(),'cashflow_eur':(qty*price).to_numpy(),'fee_eur':fee.to_numpy()}))
    ledger=pd.concat(rows,ignore_index=True)
    np.testing.assert_allclose(ledger.cashflow_eur.sum()-ledger.fee_eur.sum()-out.degradation_eur.sum(),out.net_margin_eur.sum(),atol=1e-6,rtol=0)
    return out,ledger
