"""Run from repo root: python scripts/analyse_fundamentals.py [source directory]."""
import sys, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from market_flex.prices import load_prices
from market_flex.fundamentals import load_germany, load_france, analyse

NAMES = {
 'de_price':'GUI_ENERGY_PRICES_202312312300-202412312300 (1).csv',
 'fr_price':'GUI_ENERGY_PRICES_202312312300-202412312300.csv',
 'generation':'Actual_generation_202312292300_202501022300_Quarterhour.csv',
 'consumption':'Actual_consumption_202312292300_202501022300_Quarterhour.csv',
 'france':'eco2mix-national-cons-def.csv',
}
def run(source):
    paths={k:Path(source)/v for k,v in NAMES.items()}
    prices=pd.concat([load_prices(paths['de_price'],'DE-LU','Sequence 1'),load_prices(paths['fr_price'],'FR','Without Sequence')],axis=1)
    de,audit_de=load_germany(paths['generation'],paths['consumption'])
    fr,audit_fr=load_france(paths['france'])
    combined=analyse(prices,de,fr)
    processed=ROOT/'data/processed'; processed.mkdir(parents=True,exist_ok=True)
    out=ROOT/'reports'; (out/'figures').mkdir(parents=True,exist_ok=True)
    combined.to_csv(processed/'fundamentals_prices_2024_hourly.csv',index=False)
    audit={**audit_de,**audit_fr,'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths.values()}}
    summary=[];bins=[];cases=[]
    for zone in ['DE-LU','FR']:
        f=combined[combined.zone.eq(zone)];v=f[f.fundamentals_valid].copy()
        audit[zone]={'complete_hours':len(v),'missing_hours':int((~f.fundamentals_valid).sum()),'missing_nuclear_hours':int(f.nuclear_mw.isna().sum())}
        for label,subset in [('all_valid',v),('negative_price',v[v.price_eur_mwh<0]),('nonnegative_price',v[v.price_eur_mwh>=0])]:
            summary.append({'zone':zone,'group':label,'hours':len(subset),**{c:subset[c].mean() for c in ['price_eur_mwh','demand_mw','wind_mw','solar_mw','residual_load_mw']}})
        v['decile']=pd.qcut(v.residual_load_mw,10,labels=False)+1
        b=v.groupby('decile').agg(hours=('price_eur_mwh','size'),residual_load_mw=('residual_load_mw','mean'),price_eur_mwh=('price_eur_mwh','mean')).reset_index();b['zone']=zone;bins.append(b)
        for kind,selected in [('highest_price',f.nlargest(3,'price_eur_mwh')),('lowest_price',f.nsmallest(3,'price_eur_mwh'))]:
            selected=selected.copy();selected['case']=kind;cases.append(selected)
    summary=pd.DataFrame(summary);summary.to_csv(out/'fundamentals_summary_2024.csv',index=False)
    bins=pd.concat(bins);bins.to_csv(out/'residual_load_deciles_2024.csv',index=False)
    pd.concat(cases).to_csv(out/'price_cases_2024.csv',index=False)
    (out/'fundamentals_validation_2024.json').write_text(json.dumps(audit,indent=2))
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True)
    for ax,zone,color in zip(axes,['DE-LU','FR'],['#215D9C','#C96532']):
        b=bins[bins.zone.eq(zone)]
        ax.plot(b.residual_load_mw/1000,b.price_eur_mwh,marker='o',color=color,lw=2)
        ax.set_title(zone,loc='left',weight='bold');ax.set_xlabel('Mean residual load in decile (GW)');ax.grid(alpha=.2)
    axes[0].set_ylabel('Mean day-ahead price in decile (EUR/MWh)')
    fig.suptitle('2024 | Prices rise across residual-load deciles',fontsize=16,weight='bold')
    fig.text(.06,.025,'Descriptive association, not causation or a forecast. Actual load minus wind and solar. FR excludes 1 missing hour.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.96))
    fig.savefig(out/'figures/residual_load_prices_2024.svg',bbox_inches='tight')
    fig.savefig(out/'figures/residual_load_prices_2024.png',dpi=150,bbox_inches='tight')
    plt.close(fig)
    print(summary.round(2).to_string(index=False));print(json.dumps({k:v for k,v in audit.items() if k!='input_sha256'},indent=2))
    return combined,summary

if __name__=='__main__': run(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/raw')
