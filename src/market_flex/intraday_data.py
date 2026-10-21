"""Strict canonical IDA1 validation, immutable DA alignment and paired evaluation.

Supplier-specific parsing is intentionally separate. No missing price is filled.
"""
from datetime import timedelta
import numpy as np
import pandas as pd
from market_flex.battery import Battery
from market_flex.continuous import validate
from market_flex.intraday import _check_frame, _utc

TZ = 'Europe/Berlin'


def delivery_grid(start, end):
    """Inclusive local dates, exclusive end instant; DST is retained in UTC."""
    a, b = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    if b < a:
        raise ValueError('End precedes start')
    return pd.date_range(str(a), str(b + timedelta(days=1)), freq='15min',
                         inclusive='left', tz=TZ).tz_convert('UTC')


def auction_timing(delivery_day):
    """Frozen simulation decision D-1 14:30; IDA1 gate D-1 15:00 CET/CEST."""
    prev = pd.Timestamp(delivery_day).date() - timedelta(days=1)
    decision = pd.Timestamp(f'{prev} 14:30', tz=TZ).tz_convert('UTC')
    gate = pd.Timestamp(f'{prev} 15:00', tz=TZ).tz_convert('UTC')
    return decision, gate


def _timestamps(series):
    # Reject naive times rather than silently assuming UTC across DST folds.
    return pd.DatetimeIndex([_utc(v) for v in series])


def validate_auction_data(frame, start, end):
    """Return sorted canonical data and coverage; malformed rows fail closed.

    A price-free missing/cancelled row is allowed but makes that whole local
    delivery day ineligible. An absent row also makes the day ineligible.
    decoupled/unknown are quarantined even if a price exists.
    """
    required = {'delivery_start','delivery_end','zone','auction','price_eur_mwh','status'}
    if not required.issubset(frame):
        raise ValueError('Missing canonical columns: ' + str(sorted(required-set(frame))))
    f = frame.copy(deep=True)
    if not f.zone.eq('DE-LU').all() or not f.auction.eq('IDA1').all():
        raise ValueError('Expected DE-LU SIDC IDA1 only')
    if not f.status.isin(['cleared','cancelled','missing','decoupled','unknown']).all():
        raise ValueError('Unknown auction status label')
    starts, ends = _timestamps(f.delivery_start), _timestamps(f.delivery_end)
    if not starts.is_unique:
        raise ValueError('Duplicate delivery instants')
    if not ((ends-starts) == pd.Timedelta(minutes=15)).all():
        raise ValueError('Intervals must last exactly 15 minutes')
    grid = delivery_grid(start,end)
    if not starts.isin(grid).all():
        raise ValueError('Out-of-window or non-quarter-hour delivery start')
    f['price_eur_mwh'] = pd.to_numeric(f.price_eur_mwh,errors='raise')
    if np.isinf(f.price_eur_mwh).any():
        raise ValueError('Infinite clearing price')
    if not np.isfinite(f.loc[f.status.eq('cleared'),'price_eur_mwh']).all():
        raise ValueError('Cleared interval requires a finite price')
    if f.loc[f.status.isin(['cancelled','missing']),'price_eur_mwh'].notna().any():
        raise ValueError('Cancelled/missing interval cannot supply a settlement price')
    if 'volume_mwh' in f:
        f['volume_mwh']=pd.to_numeric(f.volume_mwh,errors='raise')
        present=f.volume_mwh.dropna()
        if not np.isfinite(present).all() or (present<0).any():
            raise ValueError('Invalid contextual auction volume')
    f['delivery_start']=starts;f['delivery_end']=ends
    f.index=starts;f.index.name='timestamp_utc';f=f.sort_index()
    days=[]
    for day in sorted(set(grid.tz_convert(TZ).date)):
        expected=grid[grid.tz_convert(TZ).date==day]
        part=f.reindex(expected)
        cleared=part.status.eq('cleared') & part.price_eur_mwh.notna()
        days.append({'day_local':str(day),'expected_intervals':len(expected),
                     'present_intervals':int(expected.isin(f.index).sum()),
                     'cleared_intervals':int(cleared.sum()),'eligible':bool(cleared.all())})
    report={'start':str(start),'end':str(end),'expected_intervals':len(grid),
            'present_intervals':len(f),'missing_intervals':len(grid.difference(starts)),
            'eligible_days':sum(d['eligible'] for d in days),'days':days,
            'policy':'whole-day no adjustment on incomplete, cancelled, decoupled or unknown data',
            'execution_or_licence_verified':False}
    return f,report


def check_information(issued_at, predictor_available_at, decision_at):
    decision=_utc(decision_at)
    if _utc(issued_at)>decision or any(_utc(v)>decision for v in predictor_available_at):
        raise ValueError('Information published after decision')


def expand_da_quarterhours(da, battery=Battery()):
    """Preserve every original trade and fee; interpolate SOC using constant power.

    Original hourly/half-hour power is held constant over its quarter-hours.
    Aggregate cashflows, energy, fees and boundary SOC are reconciled.
    """
    _check_frame(da)
    validate(da,battery,float(da.soc_start_mwh.iloc[0]),float(da.soc_end_mwh.iloc[-1]))
    rows=[]; times=[]
    for stamp,row in da.iterrows():
        n=int(round(row.dt_hours/.25))
        for k in range(n):
            out=row.copy(); out['source_da_start_utc']=stamp
            out['dt_hours']=.25
            for col in ['signed_da_position_mwh','transaction_cost_eur','gross_margin_eur','net_margin_eur','degradation_eur']:
                if col in out:out[col]=row[col]/n
            change=row.soc_end_mwh-row.soc_start_mwh
            out['soc_start_mwh']=row.soc_start_mwh+change*k/n
            out['soc_end_mwh']=row.soc_start_mwh+change*(k+1)/n
            rows.append(out);times.append(stamp+pd.Timedelta(minutes=15*k))
    q=pd.DataFrame(rows,index=pd.DatetimeIndex(times));q.index.name=da.index.name
    _check_frame(q)
    validate(q,battery,float(da.soc_start_mwh.iloc[0]),float(da.soc_end_mwh.iloc[-1]))
    for stamp,g in q.groupby('source_da_start_utc'):
        orig=da.loc[stamp]
        np.testing.assert_allclose(g.signed_da_position_mwh.sum(),orig.signed_da_position_mwh,atol=1e-8,rtol=0)
        np.testing.assert_allclose((g.signed_da_position_mwh*g.actual_eur_mwh).sum(),orig.signed_da_position_mwh*orig.actual_eur_mwh,atol=1e-8,rtol=0)
        if 'transaction_cost_eur' in da:
            np.testing.assert_allclose(g.transaction_cost_eur.sum(),orig.transaction_cost_eur,atol=1e-8,rtol=0)
    return q


def evaluate_adjustment(da, settled, battery=Battery()):
    """Matched ledger metrics; physical infeasibility prevents reporting success."""
    _check_frame(da)
    if not da.index.equals(settled.index):
        raise ValueError('Unmatched evaluation intervals')
    numeric=['dt_hours','charge_mw','discharge_mw','soc_start_mwh','soc_end_mwh',
             'da_cashflow_eur','id_cashflow_eur','da_fee_eur','id_fee_eur','degradation_eur',
             'signed_id_position_mwh','id_buy_mwh','id_sell_mwh','actual_id_eur_mwh',
             'original_da_net_margin_eur','net_margin_eur','incremental_margin_eur']
    if not set(numeric).issubset(settled) or not np.isfinite(settled[numeric].to_numpy()).all():
        raise ValueError('Missing or nonfinite settlement accounting')
    if (settled[['id_buy_mwh','id_sell_mwh','id_fee_eur','da_fee_eur']] < -1e-6).any().any():
        raise ValueError('Negative trade volume or fee')
    np.testing.assert_allclose(settled.id_buy_mwh*settled.id_sell_mwh,0,atol=1e-6,rtol=0)
    np.testing.assert_allclose(settled.signed_id_position_mwh,settled.id_sell_mwh-settled.id_buy_mwh,atol=1e-6,rtol=0)
    np.testing.assert_allclose(settled.id_cashflow_eur,settled.signed_id_position_mwh*settled.actual_id_eur_mwh,atol=1e-6,rtol=0)
    np.testing.assert_allclose(settled.da_fee_eur,da.get('transaction_cost_eur',0),atol=1e-6,rtol=0)
    np.testing.assert_allclose(settled.degradation_eur,battery.degradation_eur_per_mwh_discharged*settled.discharge_mw*settled.dt_hours,atol=1e-6,rtol=0)
    validate(settled,battery,float(da.soc_start_mwh.iloc[0]),float(da.soc_end_mwh.iloc[-1]))
    np.testing.assert_allclose(settled.dt_hours,da.dt_hours,atol=0,rtol=0)
    np.testing.assert_allclose(settled.da_cashflow_eur,da.signed_da_position_mwh*da.actual_eur_mwh,atol=1e-6,rtol=0)
    residual=(settled.discharge_mw-settled.charge_mw)*settled.dt_hours-da.signed_da_position_mwh-settled.signed_id_position_mwh
    np.testing.assert_allclose(residual,0,atol=1e-6,rtol=0)
    old_wear=battery.degradation_eur_per_mwh_discharged*da.discharge_mw*da.dt_hours
    original=da.signed_da_position_mwh*da.actual_eur_mwh-da.get('transaction_cost_eur',0)-old_wear
    combined=settled.da_cashflow_eur+settled.id_cashflow_eur-settled.da_fee_eur-settled.id_fee_eur-settled.degradation_eur
    np.testing.assert_allclose(original,settled.original_da_net_margin_eur,atol=1e-6,rtol=0)
    np.testing.assert_allclose(combined,settled.net_margin_eur,atol=1e-6,rtol=0)
    delta=combined-original
    np.testing.assert_allclose(delta,settled.incremental_margin_eur,atol=1e-6,rtol=0)
    daily=delta.groupby(delta.index.tz_convert(TZ).date).sum()
    return {'da_only_margin_eur':float(original.sum()),'combined_margin_eur':float(combined.sum()),
            'incremental_margin_eur':float(delta.sum()),
            'losing_adjustment_days':int((daily < -1e-6).sum()),
            'worst_daily_adjustment_eur':float(daily.min()),
            'id_traded_mwh':float((settled.id_buy_mwh+settled.id_sell_mwh).sum()),
            'id_cashflow_eur':float(settled.id_cashflow_eur.sum()),
            'id_sales_cashflow_eur':float((settled.id_sell_mwh*settled.actual_id_eur_mwh).sum()),
            'id_purchase_expenditure_eur':float((settled.id_buy_mwh*settled.actual_id_eur_mwh).sum()),
            'id_buy_mwh':float(settled.id_buy_mwh.sum()),'id_sell_mwh':float(settled.id_sell_mwh.sum()),
            'original_cycling_cost_eur':float(old_wear.sum()),
            'revised_cycling_cost_eur':float(settled.degradation_eur.sum()),
            'id_fees_eur':float(settled.id_fee_eur.sum()),
            'change_cycling_cost_eur':float((settled.degradation_eur-old_wear).sum()),
            'change_discharged_mwh':float(((settled.discharge_mw-da.discharge_mw)*da.dt_hours).sum()),
            'max_energy_residual_mwh':float(residual.abs().max()),'physical_feasible':True,
            'intervals':len(da),'days':len(daily)}
