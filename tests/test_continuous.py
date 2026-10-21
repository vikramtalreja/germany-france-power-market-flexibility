import unittest
import numpy as np
import pandas as pd
from market_flex.battery import Battery
from market_flex.continuous import issued_forecast,optimise_horizon,projected_opening,rolling_run,settle_committed

class ContinuousTests(unittest.TestCase):
    def prices(self,start="2025-03-20",end="2025-04-02"):
        idx=pd.date_range(start,end,freq="h",inclusive="left",tz="Europe/Berlin").tz_convert("UTC")
        return pd.Series(60+40*np.sin(2*np.pi*idx.tz_convert("Europe/Berlin").hour/24),index=idx)
    def test_two_day_forecast_cannot_read_future(self):
        p=self.prices();target=p.loc["2025-03-29 23:00":"2025-03-31 21:00"].index
        a,cutoff,_=issued_forecast(p,target)
        q=p.copy();q.loc[q.index>=cutoff]=999999
        b,_,_=issued_forecast(q,target)
        pd.testing.assert_series_equal(a,b)
        self.assertEqual(len(target),47)
    def test_boundary_projection_preserves_commitment(self):
        idx=pd.date_range("2025-01-08",periods=24,freq="h",tz="Europe/Berlin").tz_convert("UTC")
        g=optimise_horizon(pd.Series(np.arange(24)*10,index=idx),1,0.4)
        before=g.copy(deep=True);cutoff=pd.Timestamp("2025-01-08 09:00",tz="Europe/Berlin").tz_convert("UTC")
        opening,state,change=projected_opening(g,cutoff)
        self.assertAlmostEqual(opening,.4,places=6)
        self.assertAlmostEqual(state+change,.4,places=6)
        pd.testing.assert_frame_equal(g,before)
    def test_analytical_cycle_and_fee(self):
        idx=pd.date_range("2025-01-01",periods=2,freq="h",tz="UTC")
        b=Battery(1,2,1,.5,10)
        g=optimise_horizon(pd.Series([0.,100.],index=idx),1,1,b,fee=1)
        self.assertAlmostEqual(g.forecast_net_margin_eur.sum(),88,places=6)
        h=settle_committed(g,pd.Series([100.,0.],index=idx),idx[0]-pd.Timedelta(days=1))
        self.assertAlmostEqual(h.net_margin_eur.sum(),-112,places=6)
        np.testing.assert_allclose(h.charge_mw,g.charge_mw)
    def test_soc_carries_through_spring_clock_change(self):
        p=self.prices()
        h,a=rolling_run(p,"2025-03-29","2025-03-31",terminal_fraction=0)
        self.assertEqual(len(h),71)
        self.assertEqual(a.committed_hours.tolist(),[24,23,24])
        np.testing.assert_allclose(h.soc_end_mwh.iloc[:-1],h.soc_start_mwh.iloc[1:],atol=1e-6)
        self.assertAlmostEqual(h.soc_end_mwh.iloc[-1],1,places=6)
        self.assertTrue((a.provisional_hours.iloc[:-1]>0).all())
    def test_negative_price_no_simultaneous_dispatch(self):
        idx=pd.date_range("2025-01-01",periods=3,freq="h",tz="UTC")
        g=optimise_horizon(pd.Series([-100.,-100.,20.],index=idx),1,1)
        self.assertLess((g.charge_mw*g.discharge_mw).abs().max(),1e-7)
        self.assertAlmostEqual(g.soc_end_mwh.iloc[-1],1,places=6)

if __name__=="__main__":unittest.main()
