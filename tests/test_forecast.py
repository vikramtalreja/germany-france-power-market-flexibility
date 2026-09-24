import unittest
import numpy as np
import pandas as pd
from market_flex.forecast import forecast,settle,MODELS
from market_flex.battery import optimise,Battery

class ForecastTests(unittest.TestCase):
    def test_future_changes_do_not_change_forecast(self):
        idx=pd.date_range('2024-01-01','2024-01-20',freq='h',tz='UTC');p=pd.Series(np.arange(len(idx),dtype=float),index=idx)
        target=pd.date_range('2024-01-10','2024-01-11',freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
        changed=p.copy();changed.loc[changed.index>=pd.Timestamp('2024-01-09',tz='Europe/Berlin')]=999999
        for m in MODELS:
            a,_=forecast(p,target,m);b,_=forecast(changed,target,m);pd.testing.assert_series_equal(a,b)
    def test_constant_profile_and_dst(self):
        for day,end,n in [('2024-03-31','2024-04-01',23),('2024-10-27','2024-10-28',25),('2024-04-01','2024-04-02',24),('2024-10-28','2024-10-29',24),('2024-04-02','2024-04-03',24)]:
            target=pd.date_range(day,end,freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
            p=pd.Series(42.,index=pd.date_range(target[0]-pd.Timedelta(days=10),target[-1],freq='h'))
            for m in MODELS:
                f,audit=forecast(p,target,m);self.assertEqual(len(f),n);self.assertTrue(f.eq(42).all())
                self.assertEqual(pd.Timestamp(audit['decision_cutoff_utc']).tz_convert('Europe/Berlin').hour,9)
    def test_realised_loss_is_allowed_and_dispatch_fixed(self):
        idx=pd.date_range('2024-01-01',periods=2,freq='h',tz='UTC')
        schedule=optimise(pd.Series([0.,100.],index=idx),Battery(round_trip_efficiency=1,degradation_eur_per_mwh_discharged=10))
        result=settle(schedule,pd.Series([100.,0.],index=idx))
        self.assertAlmostEqual(result.net_margin_eur.sum(),-110)
        pd.testing.assert_series_equal(result.charge_mw,schedule.charge_mw)
    def test_missing_history_rejected(self):
        idx=pd.date_range('2024-01-10',periods=24,freq='h',tz='UTC')
        with self.assertRaises(ValueError):forecast(pd.Series(1.,index=idx),idx,MODELS[0])
