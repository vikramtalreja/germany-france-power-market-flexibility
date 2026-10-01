import unittest
import numpy as np
import pandas as pd
from market_flex.ml import day_features,estimator,NUMERIC,select,assert_training_boundary

class MLTests(unittest.TestCase):
    def series(self):
        idx=pd.date_range('2024-01-01','2025-01-01',freq='h',inclusive='left',tz='Europe/Berlin').tz_convert('UTC')
        return pd.Series(np.arange(len(idx),dtype=float)%157,index=idx)
    def test_future_perturbation_and_frozen_predictions(self):
        p=self.series();target=p.loc['2024-02-10 23:00':'2024-02-11 22:00'].index
        x,_=day_features(p,target);changed=p.copy();changed.loc['2024-02-10 00:00':]=999999
        y,_=day_features(changed,target);pd.testing.assert_frame_equal(x,y)
        m=estimator({'family':'ridge','alpha':1});m.fit(x,np.arange(len(x)))
        np.testing.assert_allclose(m.predict(x),m.predict(y))
        scaler=m.named_steps['features'].named_transformers_['numeric']
        np.testing.assert_allclose(scaler.mean_,x[NUMERIC].mean())
        means=scaler.mean_.copy();m.predict(x*100);np.testing.assert_array_equal(means,scaler.mean_)
    def test_dst(self):
        p=self.series()
        for day,n in [('2024-03-31',23),('2024-10-27',25)]:
            target=p[p.index.tz_convert('Europe/Berlin').strftime('%Y-%m-%d')==day].index
            x,_=day_features(p,target);self.assertEqual(len(x),n)
            repeated=x[x.index.tz_convert('Europe/Berlin').hour==2]
            if n==25:np.testing.assert_allclose(repeated.iloc[0],repeated.iloc[1])
    def test_selection_near_tie(self):
        s=pd.DataFrame({'model':['a','b','c'],'net_margin_eur':[10,9.5,8],'mae_eur_mwh':[5,4,1]})
        self.assertEqual(select(s,['a','b','c']),'b')
    def test_training_boundary_rejects_d_minus_one(self):
        with self.assertRaises(AssertionError):assert_training_boundary(pd.date_range('2024-08-31',periods=1,tz='UTC'),'2024-09-01')
