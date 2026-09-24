"""Price-taking, perfect-foresight daily BESS MILP in Pyomo."""
from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd
import pyomo.environ as pyo

@dataclass(frozen=True)
class Battery:
    power_mw: float = 1.0
    energy_mwh: float = 2.0
    round_trip_efficiency: float = 0.90
    initial_fraction: float = 0.50
    degradation_eur_per_mwh_discharged: float = 10.0

    def validate(self):
        assert all(math.isfinite(v) for v in asdict(self).values())
        assert self.power_mw > 0 and self.energy_mwh > 0
        assert 0 < self.round_trip_efficiency <= 1
        assert 0 <= self.initial_fraction <= 1
        assert self.degradation_eur_per_mwh_discharged >= 0


def optimise(prices, battery=Battery()):
    """One complete local delivery day; hourly prices indexed by unique UTC times.

    End SOC equals start SOC. All trades are assumed accepted at supplied prices.
    Can also optimise a synthetic short series for analytical tests.
    """
    battery.validate()
    prices = pd.Series(prices, dtype=float)
    assert len(prices) and np.isfinite(prices).all()
    assert isinstance(prices.index, pd.DatetimeIndex) and prices.index.tz is not None
    assert prices.index.is_unique and prices.index.is_monotonic_increasing
    assert len(prices) == 1 or (np.diff(prices.index.asi8) == 3600*10**9).all()
    n=len(prices); eta=math.sqrt(battery.round_trip_efficiency)
    m=pyo.ConcreteModel();m.t=pyo.RangeSet(0,n-1);m.k=pyo.RangeSet(0,n)
    m.c=pyo.Var(m.t,bounds=(0,battery.power_mw))
    m.d=pyo.Var(m.t,bounds=(0,battery.power_mw))
    m.s=pyo.Var(m.k,bounds=(0,battery.energy_mwh))
    m.mode=pyo.Var(m.t,within=pyo.Binary)
    m.start=pyo.Constraint(expr=m.s[0]==battery.initial_fraction*battery.energy_mwh)
    m.end=pyo.Constraint(expr=m.s[n]==battery.initial_fraction*battery.energy_mwh)
    m.balance=pyo.Constraint(m.t,rule=lambda m,t:m.s[t+1]==m.s[t]+eta*m.c[t]-m.d[t]/eta)
    m.charge_mode=pyo.Constraint(m.t,rule=lambda m,t:m.c[t]<=battery.power_mw*m.mode[t])
    m.discharge_mode=pyo.Constraint(m.t,rule=lambda m,t:m.d[t]<=battery.power_mw*(1-m.mode[t]))
    m.objective=pyo.Objective(expr=sum(float(prices.iloc[t])*(m.d[t]-m.c[t])-battery.degradation_eur_per_mwh_discharged*m.d[t] for t in m.t),sense=pyo.maximize)
    solver=pyo.SolverFactory('highs');solver.options['mip_rel_gap']=1e-8
    result=solver.solve(m)
    if not pyo.check_optimal_termination(result):raise RuntimeError(str(result.solver))
    out=pd.DataFrame({'price_eur_mwh':prices,'charge_mw':[pyo.value(m.c[t]) for t in m.t],'discharge_mw':[pyo.value(m.d[t]) for t in m.t],'soc_start_mwh':[pyo.value(m.s[t]) for t in m.t],'soc_end_mwh':[pyo.value(m.s[t+1]) for t in m.t]})
    out.index.name='timestamp_utc'
    out['gross_margin_eur']=out.price_eur_mwh*(out.discharge_mw-out.charge_mw)
    out['degradation_eur']=battery.degradation_eur_per_mwh_discharged*out.discharge_mw
    out['net_margin_eur']=out.gross_margin_eur-out.degradation_eur
    validate_dispatch(out,battery)
    return out


def validate_dispatch(out,battery):
    eta=math.sqrt(battery.round_trip_efficiency);tol=1e-6
    assert out[['charge_mw','discharge_mw']].min().min()>=-tol
    assert out[['charge_mw','discharge_mw']].max().max()<=battery.power_mw+tol
    assert (out.charge_mw*out.discharge_mw).abs().max()<tol
    assert out[['soc_start_mwh','soc_end_mwh']].min().min()>=-tol
    assert out[['soc_start_mwh','soc_end_mwh']].max().max()<=battery.energy_mwh+tol
    assert (out.soc_end_mwh-out.soc_start_mwh-eta*out.charge_mw+out.discharge_mw/eta).abs().max()<tol
    assert abs(out.soc_start_mwh.iloc[0]-battery.initial_fraction*battery.energy_mwh)<tol
    assert abs(out.soc_end_mwh.iloc[-1]-out.soc_start_mwh.iloc[0])<tol
    assert np.allclose(out.soc_start_mwh.iloc[1:],out.soc_end_mwh.iloc[:-1],atol=tol)
    assert out.net_margin_eur.sum()>=-tol  # Idle is feasible.
