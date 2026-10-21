"""Validate a PRIVATE canonical CSV; writes coverage only, never raw prices.

python scripts/validate_intraday_data.py input.csv --start 2025-01-09 --end 2025-09-30 --report report.json
Use only after provider-specific parsing has mapped columns and timezone offsets.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from market_flex.intraday_data import validate_auction_data

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv',type=Path);p.add_argument('--start',required=True);p.add_argument('--end',required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    _,report=validate_auction_data(pd.read_csv(a.csv),a.start,a.end)
    report['source_sha256']=hashlib.sha256(a.csv.read_bytes()).hexdigest()
    report['validation_scope']='schema_and_coverage_only; rights_and_execution_require_separate_review'
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='days'},indent=2))
