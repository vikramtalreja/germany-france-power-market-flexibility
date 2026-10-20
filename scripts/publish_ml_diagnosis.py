"""Report verified accounting and observed actions, without attributing untested causes."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/"reports"
delta=pd.read_csv(out/"ml_diagnosis_hourly_reconciled_daily_2025.csv")
cases=pd.read_csv(out/"ml_diagnosis_cases_2025.csv")
h=pd.read_csv(out/"ml_diagnosis_selected_dispatch_2025.csv")
h.timestamp_utc=pd.to_datetime(h.timestamp_utc,utc=True)
lines=["# Hourly ML diagnosis — reconstructed and reconciled schedules","",
"Full dispatch has been regenerated from byte-verified public inputs and frozen model settings. Daily financial results reconcile with the earlier published backtest. Original hourly hashes were not retained; hourly tie-breaking may differ even when daily results match. These are reconstructed schedules, not a recovered original binary file.","",
"## Full-period RF minus seven-day accounting","",
"Sales and purchases retain negative-price signs. Net difference = sales difference − purchase-expenditure difference − cycling-cost difference.","",
"| Market | Sales difference EUR | Purchase expenditure difference EUR | Cycling cost difference EUR | Net difference EUR |",
"|---|---:|---:|---:|---:|"]
for z,g in delta.groupby("zone"):
    s=g.sum(numeric_only=True)
    lines.append(f"| {z} | {s.sales_eur:.2f} | {s.purchases_eur:.2f} | {s.degradation_eur:.2f} | {s.net_margin_eur:.2f} |")
lines+=["","These are exact accounting contributions; price and quantity changes are mixed in each component. A negative purchase-expenditure difference helps margin. A negative sales difference hurts margin. They do not independently establish a causal forecasting failure.","",
"## Selected daily decisions","",
"Both adverse and favourable cases are retained. The largest adverse/beneficial hourly cashflows below are booked contributions, not isolated profitable trades: battery SOC links charging and discharge across hours.",""]
observations=[]
for c in cases.itertuples():
    sub=h[(h.zone==c.zone)&(h.day_cet==c.day_cet)].copy()
    b=sub[sub.model=="seven_day_same_hour"].set_index("timestamp_utc").sort_index()
    f=sub[sub.model==c.rf_model].set_index("timestamp_utc").sort_index()
    actual=b.actual_eur_mwh
    hourdelta=f.net_margin_eur-b.net_margin_eur
    row=delta[(delta.zone==c.zone)&(delta.day_cet==c.day_cet)].iloc[0]
    lines += [f"### {c.zone} — {c.day_cet} ({c.case_type} {c.rank})","",
    f"RF net EUR{c.rf_net_eur:.2f}; baseline EUR{c.baseline_net_eur:.2f}; gap EUR{c.net_difference_eur:+.2f}. Sales contribution EUR{row.sales_eur:+.2f}; purchase contribution EUR{-row.purchases_eur:+.2f}; cycling contribution EUR{-row.degradation_eur:+.2f}.","",
    "| Strategy | Forecast range EUR/MWh | Charged MWh | Discharged MWh | Weighted purchase price | Weighted sale price |",
    "|---|---:|---:|---:|---:|---:|"]
    for label,g in [("Seven-day",b),("RF",f)]:
        charge=g.charge_mw.sum();discharge=g.discharge_mw.sum()
        buy=(g.actual_eur_mwh*g.charge_mw).sum()/charge if charge>1e-8 else None
        sell=(g.actual_eur_mwh*g.discharge_mw).sum()/discharge if discharge>1e-8 else None
        buys="idle" if buy is None else f"{buy:.2f}"
        sells="idle" if sell is None else f"{sell:.2f}"
        lines.append(f"| {label} | {g.forecast_eur_mwh.min():.2f} to {g.forecast_eur_mwh.max():.2f} | {charge:.3f} | {discharge:.3f} | {buys} | {sells} |")
    lines.append("")
    for kind,t in [("Largest adverse",hourdelta.idxmin()),("Largest favourable",hourdelta.idxmax())]:
        a=b.loc[t];r=f.loc[t]
        text=(f"{kind} hourly RF-minus-baseline contribution: EUR{hourdelta.loc[t]:+.2f} at "
              f"{t.tz_convert('Europe/Berlin').strftime('%H:%M %Z')}, actual price EUR{a.actual_eur_mwh:.2f}/MWh. "
              f"Baseline/RF charge: {a.charge_mw:.3f}/{r.charge_mw:.3f} MW; discharge: {a.discharge_mw:.3f}/{r.discharge_mw:.3f} MW; "
              f"opening SOC: {a.soc_start_mwh:.3f}/{r.soc_start_mwh:.3f} MWh.")
        lines += [text,""]
    if f.discharge_mw.sum()<1e-8:
        lines += ["RF chooses inactivity across this day under its forecast and the fixed costs/constraints. The baseline captures positive realised value. This supports a missed-opportunity diagnosis for this schedule; it does not establish why the forest learned this forecast shape.",""]
    for label,g in [("Seven-day",b),("RF",f)]:
        missed=(g.actual_eur_mwh>200)&(g.forecast_eur_mwh<=200)
        lines.append(f"{label}: {int(missed.sum())} missed spike classifications; discharged {g.loc[missed,'discharge_mw'].sum():.3f} MWh in those hours.")
    lines+=["",f"![Price, charge, discharge and SOC comparison](figures/ml_diagnosis_{c.zone}_{c.day_cet}.svg)",""]
lines+=["## Scope and reproducibility","",
"- No model changes, retuning or new holdout claims. This diagnoses the inspected January–September 2025 period.",
"- Fixed daily 50% starting/ending SOC, 1 MW / 2 MWh, 90% round-trip efficiency and EUR10/MWh discharged cycling cost.",
"- Physical feasibility, hourly continuity, unchanged settlement accounting and published daily totals are checked before publication.",
"- [Recovery audit](dispatch_recovery_2025.json), [all daily accounting](ml_diagnosis_hourly_reconciled_daily_2025.csv), [selected hourly schedules](ml_diagnosis_selected_dispatch_2025.csv).",
"- [Full compressed hourly data and price inputs](../data/recovered/README.md).",
"- Reproduce with scripts/recover_dispatch_2025.py, scripts/diagnose_ml_2025.py and scripts/publish_ml_diagnosis.py, or use the Recover dispatch and diagnose ML GitHub Actions workflow.",
"- Continuous SOC remains the next implementation; the results here retain the original daily-reset assumptions.",""]
(out/"ml_diagnosis_hourly_2025.md").write_text("\n".join(lines))
