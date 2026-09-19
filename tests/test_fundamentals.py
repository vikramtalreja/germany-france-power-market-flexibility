import unittest
import pandas as pd
from market_flex.fundamentals import complete_hourly, deduplicate_actuals

class TimeSeriesChecks(unittest.TestCase):
    def test_incomplete_hour_remains_missing(self):
        f = pd.DataFrame({'mw':[10.,30.,50.]}, index=pd.date_range('2023-12-31T23:00Z',periods=3,freq='30min'))
        h = complete_hourly(f,2)
        self.assertEqual(h.iloc[0,0],20.)
        self.assertTrue(pd.isna(h.iloc[1,0]))

    def test_conflicting_duplicates_fail(self):
        f = pd.DataFrame({'mw':[10.,20.]},index=pd.to_datetime(['2024-03-31T01:00Z']*2))
        with self.assertRaises(ValueError): deduplicate_actuals(f)
        f.iloc[1,0]=10.
        self.assertEqual(len(deduplicate_actuals(f)),1)

    def test_fall_back_is_two_distinct_hours(self):
        local = pd.DatetimeIndex(['2024-10-27 02:00','2024-10-27 02:15','2024-10-27 02:30','2024-10-27 02:45']*2)
        utc = local.tz_localize('Europe/Berlin',ambiguous='infer').tz_convert('UTC')
        self.assertTrue(utc.is_unique)
        self.assertTrue((utc[1:]-utc[:-1]==pd.Timedelta('15min')).all())

if __name__=='__main__': unittest.main()
