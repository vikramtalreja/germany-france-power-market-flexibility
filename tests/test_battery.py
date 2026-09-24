import unittest
import pandas as pd
from market_flex.battery import Battery,optimise

def prices(values):
    return pd.Series(values,index=pd.date_range('2024-01-01',periods=len(values),freq='h',tz='UTC'))
class BatteryTests(unittest.TestCase):
    def test_flat_positive_idle(self):
        result=optimise(prices([100]*24))
        self.assertAlmostEqual(result.net_margin_eur.sum(),0,places=5)
    def test_two_hour_analytical_arbitrage(self):
        result=optimise(prices([0,100]),Battery(round_trip_efficiency=1,degradation_eur_per_mwh_discharged=10))
        self.assertAlmostEqual(result.net_margin_eur.sum(),90,places=5)
        self.assertAlmostEqual(result.charge_mw.sum(),1,places=5)
    def test_negative_prices_no_simultaneous_operation(self):
        result=optimise(prices([-100,-100]),Battery())
        self.assertLess((result.charge_mw*result.discharge_mw).abs().max(),1e-7)
        self.assertAlmostEqual(result.net_margin_eur.sum(),1,places=5)
    def test_dst_day_lengths(self):
        for day,next_day,n in [('2024-03-31','2024-04-01',23),('2024-10-27','2024-10-28',25)]:
            index=pd.date_range(day,next_day,freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
            result=optimise(pd.Series(100.,index=index))
            self.assertEqual(len(result),n)
if __name__=='__main__':unittest.main()
