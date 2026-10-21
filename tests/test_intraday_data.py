import unittest
import numpy as np
import pandas as pd
from market_flex.intraday_data import delivery_grid, auction_timing, validate_auction_data, check_information, expand_da_quarterhours, evaluate_adjustment
from market_flex.battery import Battery
from market_flex.continuous import optimise_horizon, settle_committed
from market_flex.intraday import plan_adjustment, settle_adjustment

class DataTests(unittest.TestCase):
    def frame(self,day):
        i=delivery_grid(day,day)
        return pd.DataFrame({'delivery_start':i.astype(str),'delivery_end':(i+pd.Timedelta(minutes=15)).astype(str),'zone':'DE-LU','auction':'IDA1','price_eur_mwh':-10.,'status':'cleared'})
    def test_dst_days_have_92_96_100_intervals(self):
        for day,n in [('2025-03-30',92),('2025-01-09',96),('2025-10-26',100)]:
            f,report=validate_auction_data(self.frame(day),day,day)
            self.assertEqual(len(f),n); self.assertEqual(report['eligible_days'],1)
    def test_naive_times_rejected(self):
        f=self.frame('2025-10-26');f.loc[0,'delivery_start']='2025-10-26 02:00'
        with self.assertRaises(ValueError):validate_auction_data(f,'2025-10-26','2025-10-26')
    def test_duplicate_instant_rejected(self):
        f=self.frame('2025-01-09');f=pd.concat([f,f.iloc[[0]]])
        with self.assertRaises(ValueError):validate_auction_data(f,'2025-01-09','2025-01-09')
    def test_wrong_product_and_off_grid_rejected(self):
        for col,value in [('auction','ID1'),('zone','FR'),('delivery_start','2025-01-09T00:01:00Z')]:
            f=self.frame('2025-01-09');f.loc[0,col]=value
            with self.assertRaises(ValueError):validate_auction_data(f,'2025-01-09','2025-01-09')
    def test_missing_row_not_imputed(self):
        f=self.frame('2025-01-09').drop(2);valid,r=validate_auction_data(f,'2025-01-09','2025-01-09')
        self.assertEqual(len(valid),95);self.assertEqual(r['missing_intervals'],1);self.assertEqual(r['eligible_days'],0)
    def test_cancelled_and_decoupled_quarantined(self):
        for status in ['cancelled','decoupled','unknown']:
            f=self.frame('2025-01-09');f.loc[0,'status']=status;f.loc[0,'price_eur_mwh']=np.nan
            _,r=validate_auction_data(f,'2025-01-09','2025-01-09');self.assertEqual(r['eligible_days'],0)
    def test_cleared_missing_price_and_cancelled_price_rejected(self):
        for status,price in [('cleared',np.nan),('cancelled',20.),('cleared',np.inf)]:
            f=self.frame('2025-01-09');f.loc[0,['status','price_eur_mwh']]=[status,price]
            with self.assertRaises(ValueError):validate_auction_data(f,'2025-01-09','2025-01-09')
    def test_local_gate_follows_season(self):
        for day,utc_hour in [('2025-01-09',14),('2025-07-09',13),('2025-03-30',14),('2025-10-26',13)]:
            decision,gate=auction_timing(day)
            self.assertEqual(gate.hour,utc_hour);self.assertEqual(gate-decision,pd.Timedelta(minutes=30))
    def test_late_predictors_rejected(self):
        check_information('2025-01-08T13:00Z',['2025-01-08T12:00Z'],'2025-01-08T13:30Z')
        with self.assertRaises(ValueError):check_information('2025-01-08T13:00Z',['2025-01-08T14:00Z'],'2025-01-08T13:30Z')
    def test_full_dst_da_alignment_and_fee_preservation(self):
        b=Battery(round_trip_efficiency=1.,degradation_eur_per_mwh_discharged=0.)
        for day in ['2025-03-30','2025-10-26']:
            i=delivery_grid(day,day)[::4];p=pd.Series(np.resize([10.,100.],len(i)),index=i)
            da=settle_committed(optimise_horizon(p,1,1,b,fee=1.),p,'2025-01-01T00:00Z');before=da.copy(deep=True)
            q=expand_da_quarterhours(da,b)
            self.assertTrue(q.index.equals(delivery_grid(day,day)))
            self.assertAlmostEqual(da.transaction_cost_eur.sum(),q.transaction_cost_eur.sum())
            self.assertAlmostEqual((da.signed_da_position_mwh*p).sum(),(q.signed_da_position_mwh*q.actual_eur_mwh).sum())
            pd.testing.assert_frame_equal(da,before)
    def test_paired_metrics_and_tampering(self):
        b=Battery(round_trip_efficiency=1.,degradation_eur_per_mwh_discharged=0.)
        i=pd.date_range('2025-01-09',periods=4,freq='h',tz='UTC');p=pd.Series([10.,100.,20.,80.],index=i)
        da=settle_committed(optimise_horizon(p,1,1,b),p,'2025-01-08T08:00Z')
        forecast=pd.Series([100.,10.,80.,20.],index=i)
        plan=plan_adjustment(da,forecast,'2025-01-08T13:00Z','2025-01-08T13:30Z','2025-01-08T14:00Z',2,2,battery=b)
        settled,_=settle_adjustment(da,plan,p,b)
        result=evaluate_adjustment(da,settled,b)
        self.assertAlmostEqual(result['incremental_margin_eur'],-308.)
        self.assertEqual(result['losing_adjustment_days'],1)
        self.assertAlmostEqual(result['id_traded_mwh'],8.)
        settled.loc[i[0],'da_cashflow_eur']+=1
        with self.assertRaises(AssertionError):evaluate_adjustment(da,settled,b)

if __name__=='__main__':unittest.main()
