import unittest
import numpy as np
import pandas as pd
from market_flex.battery import Battery
from market_flex.continuous import optimise_horizon,settle_committed
from market_flex.intraday import plan_adjustment,settle_adjustment

class IntradayTests(unittest.TestCase):
    def setUp(self):
        self.b=Battery(round_trip_efficiency=1.,degradation_eur_per_mwh_discharged=0.)
        self.i=pd.date_range('2025-01-09',periods=4,freq='h',tz='UTC')
        self.price=pd.Series([10.,100.,20.,80.],index=self.i)
        self.da=settle_committed(optimise_horizon(self.price,1,1,self.b),self.price,'2025-01-08T08:00Z')
        self.forecast=pd.Series([100.,10.,80.,20.],index=self.i)
    def plan(self,**kw):
        args=dict(forecast_issued_at='2025-01-08T13:00Z',decision_at='2025-01-08T13:30Z',gate_closure_at='2025-01-08T14:00Z',max_buy_mwh=2,max_sell_mwh=2,fee=1.,battery=self.b)
        args.update(kw)
        return plan_adjustment(self.da,self.forecast,**args)
    def test_preserve_da_and_reconcile(self):
        before=self.da.copy(deep=True);p=self.plan();s,l=settle_adjustment(self.da,p,self.forecast,self.b)
        pd.testing.assert_frame_equal(self.da,before)
        np.testing.assert_allclose(l[l.market.eq('DA')].cashflow_eur,self.da.signed_da_position_mwh*self.price)
        self.assertAlmostEqual(s.imbalance_mwh.abs().sum(),0.)
        self.assertGreater(s.incremental_margin_eur.sum(),0)
    def test_adverse_settlement_does_not_change_dispatch(self):
        p=self.plan();before=p.copy(deep=True)
        s,l=settle_adjustment(self.da,p,self.price,self.b)
        pd.testing.assert_frame_equal(p,before)
        self.assertLess(s.incremental_margin_eur.sum(),0)
    def test_zero_liquidity_preserves_physics(self):
        p=self.plan(max_buy_mwh=0,max_sell_mwh=0)
        np.testing.assert_allclose(p.signed_id_position_mwh,0,atol=1e-8)
        np.testing.assert_allclose(p.charge_mw,self.da.charge_mw,atol=1e-8)
    def test_future_forecast_and_closed_gate_rejected(self):
        for kw in [dict(forecast_issued_at='2025-01-08T15:00Z'),dict(decision_at='2025-01-08T14:00Z')]:
            with self.assertRaises(ValueError):self.plan(**kw)
    def test_original_da_prices_are_sunk_for_planning(self):
        p=self.plan();self.da.actual_eur_mwh+=10000
        q=self.plan()
        np.testing.assert_allclose(p.signed_id_position_mwh,q.signed_id_position_mwh,atol=1e-8)
    def test_quarterhour_energy_units(self):
        i=pd.date_range('2025-03-30T00:00Z',periods=4,freq='15min')
        self.da=pd.DataFrame({'dt_hours':.25,'signed_da_position_mwh':0.,'actual_eur_mwh':50.,'soc_start_mwh':1.,'soc_end_mwh':1.,'charge_mw':0.,'discharge_mw':0.},index=i)
        self.forecast=pd.Series([0.,100.,0.,100.],index=i)
        p=self.plan();self.assertAlmostEqual(p.id_sell_mwh.sum(),.5)
        self.assertLessEqual(p.id_buy_mwh.max(),.25+1e-8)
    def test_trade_volume_caps(self):
        p=self.plan(max_buy_mwh=.1,max_sell_mwh=.2)
        self.assertLessEqual(p.id_buy_mwh.max(),.1+1e-8)
        self.assertLessEqual(p.id_sell_mwh.max(),.2+1e-8)
        self.assertLess((p.id_buy_mwh*p.id_sell_mwh).abs().max(),1e-8)
    def test_missing_intervals_rejected(self):
        self.da=self.da.drop(self.i[1]);self.forecast=self.forecast.drop(self.i[1])
        with self.assertRaises(ValueError):self.plan()

if __name__=='__main__':unittest.main()
