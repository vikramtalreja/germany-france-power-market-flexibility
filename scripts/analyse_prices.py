"""Run from repository root: python scripts/analyse_prices.py [input directory]."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from market_flex.prices import compare

frame, summary = compare(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/raw')
out = ROOT/'reports'
(out/'figures').mkdir(parents=True, exist_ok=True)
summary.to_csv(out/'price_summary_2024.csv', index_label='zone')
(ROOT/'data/processed').mkdir(parents=True, exist_ok=True)
frame.to_csv(ROOT/'data/processed/prices_2024_hourly.csv')
monthly = frame.tz_convert('Europe/Berlin').resample('MS').mean()
plt.rcParams.update({'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False})
fig, axes = plt.subplots(2,1, figsize=(11,7), sharex=True, gridspec_kw={'height_ratios':[2,1]})
for zone, color in [('DE-LU','#215D9C'),('FR','#C96532')]:
    axes[0].plot(range(12), monthly[zone], marker='o', label=zone, color=color, linewidth=2)
axes[0].set_title('Germany–France electricity prices | 2024', loc='left', weight='bold', pad=18)
axes[0].set_ylabel('Monthly mean (EUR/MWh)'); axes[0].legend(frameon=False)
axes[1].bar(range(12),monthly['spread_eur_mwh'],color='#548C83')
axes[1].set_ylabel('DE-LU minus FR\n(EUR/MWh)');axes[1].axhline(0,color='#555555',linewidth=.8)
axes[1].set_xticks(range(12),monthly.index.strftime('%b'))
for ax in axes: ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
fig.text(.08,.015,'Source: user-supplied ENTSO-E GUI exports. DE-LU: Sequence 1; FR: Without Sequence. Local delivery months.',fontsize=9)
fig.tight_layout(rect=(0,.04,1,1))
fig.savefig(out/'figures/prices_2024.svg',bbox_inches='tight')
fig.savefig(out/'figures/prices_2024.png',dpi=160,bbox_inches='tight')
print(summary.to_string());print('Mean spread:',frame['spread_eur_mwh'].mean())
print('DST days:',frame.tz_convert('Europe/Berlin').resample('D').size().loc[['2024-03-31','2024-10-27']].to_dict())
