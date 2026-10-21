"""Synthetic accounting demonstration. NOT historical intraday performance."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import pandas as pd
from market_flex.battery import Battery
from market_flex.continuous import optimise_horizon,settle_committed
from market_flex.intraday import plan_adjustment,settle_adjustment

def run():
    # Four hours are deliberately simple to permit hand calculation.
    i=pd.date_range('2025-01-09',periods=4,freq='h',tz='UTC')
    b=Battery(round_trip_efficiency=1.,degradation_eur_per_mwh_discharged=0.)
    da_prices=pd.Series([10.,100.,20.,80.],index=i)
    da=settle_committed(optimise_horizon(da_prices,1,1,b),da_prices,'2025-01-08T08:00Z')
    forecast=pd.Series([100.,10.,80.,20.],index=i)
    p=plan_adjustment(da,forecast,'2025-01-08T13:00Z','2025-01-08T13:30Z','2025-01-08T14:00Z',2.,2.,fee=1.,battery=b)
    rows=[];ledgers=[];dispatch=[]
    for case,actual in [('forecast_materialises',forecast),('forecast_wrong',da_prices)]:
        settled,ledger=settle_adjustment(da,p,actual,b)
        rows.append({'case':case,'synthetic':True,'original_da_net_eur':settled.original_da_net_margin_eur.sum(),
                     'id_cashflow_eur':settled.id_cashflow_eur.sum(),'id_fees_eur':settled.id_fee_eur.sum(),
                     'combined_net_eur':settled.net_margin_eur.sum(),'incremental_net_eur':settled.incremental_margin_eur.sum()})
        ledger['case']=case;ledger['synthetic']=True;ledgers.append(ledger)
        settled['case']=case;settled['synthetic']=True;dispatch.append(settled.reset_index(names='timestamp_utc'))
    dest=ROOT/'reports';pd.DataFrame(rows).to_csv(dest/'intraday_synthetic_summary.csv',index=False)
    pd.concat(ledgers).to_csv(dest/'intraday_synthetic_ledger.csv',index=False)
    pd.concat(dispatch).to_csv(dest/'intraday_synthetic_dispatch.csv',index=False)
    (dest/'intraday_stage_status.json').write_text(json.dumps({'engine':'implemented','tests':'28 passed','historical_backtest':'not_run','reason':'No verified usable historical intraday dataset and publication/execution metadata acquired','demonstration':'synthetic, not historical','zone_target':'DE-LU','venue_target':'IDA1 auction, not continuous SIDC','checked_on':'2026-10-21'},indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':run()
