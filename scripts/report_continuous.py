"""Report the frozen structural experiment without selecting a policy."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def write_report(metrics,daily,hourly):
    out=ROOT/"reports";figdir=out/"figures";figdir.mkdir(exist_ok=True)
    lines=["# Continuous battery operation — retrospective 2025 comparison","",
    "## What changed and why","",
    "The previous benchmark restored SOC to 50% each day. This version carries committed energy across midnight, plans two local delivery days, commits only the first, and revises the provisional second day at the next decision. The forecast remains the same seven-day mean, fixed at the issuance cutoff for both planning days. This isolates a structural modelling change without training a new forecasting model.","",
    "At D-1 09:00, the battery's opening SOC for D is projected through the remaining fixed D-1 schedule. Physical execution is assumed exact. No future actual price enters planning. Accepted day-ahead quantities and later actual-price cashflows are recorded in a separate trade ledger; intraday and reserves are not implemented.","",
    "## Frozen assumptions","",
    "- 9 January–30 September 2025 in DE-LU and France; 265 days / 6,359 hours per zone. Already inspected data: retrospective, not an unseen test.",
    "- 1 MW / 2 MWh; 90% round-trip efficiency; EUR10/MWh discharged cycling cost.",
    "- Planning terminal SOC 50% in the main scenario; 0% and 100% sensitivity cases. These apply at the provisional horizon end, not every committed midnight.",
    "- Actual initial and final evaluation SOC are 1 MWh in every case. The last horizon is shortened and the common final SOC overrides the sensitivity target.",
    "- Fee sensitivity is EUR1/MWh on each buy/sell leg, an illustrative cost, with a fee-matched daily-reset comparison.",
    "- Full-period perfect foresight is solved to optimality separately at each fee. It has the same physical and initial/final conditions and is an upper bound, not a forecast strategy.","",
    "## Results","",
    "| Market | Policy | Net margin EUR | Transaction costs EUR | Loss days | Bound gap EUR | Midnights away from 50% |",
    "|---|---|---:|---:|---:|---:|---:|"]
    for r in metrics.itertuples():
        lines.append(f"| {r.zone} | {r.policy} | {r.net_margin_eur:,.2f} | {r.transaction_cost_eur:,.2f} | {r.loss_days} | {r.oracle_gap_eur:,.2f} | {r.boundary_days_away_from_50pct} |")
    lines+=["","Policy names: continuous = main 50% planning target, zero fee; fee_1 = same target with EUR1/MWh each side; terminal_0/terminal_1 = zero-fee planning terminal sensitivities. Global oracle is non-causal perfect foresight. No winning policy is selected from these retrospective results.","",
    "## Main comparisons",""]
    for z,g in metrics.groupby("zone"):
        a=g.set_index("policy");base=a.loc["daily_reset_fee_0"];main=a.loc["continuous"]
        fee=a.loc["fee_1"];feebase=a.loc["daily_reset_fee_1"]
        lines += [f"**{z}:** continuous operation changes margin by EUR{main.net_margin_eur-base.net_margin_eur:+,.2f} against daily reset at zero fee. With the illustrative fee, the difference against the fee-matched reset is EUR{fee.net_margin_eur-feebase.net_margin_eur:+,.2f}. The main strategy ends {int(main.boundary_days_away_from_50pct)} of the 264 internal days away from 50% SOC.",""]
    lines+=["![Cumulative margin and boundary SOC](figures/continuous_2025.svg)","",
    "Loss-day counts are calendar accounting windows. With energy carried across days, purchases today may support sales tomorrow; daily profits are not independent cycles. Equal final inventory makes the full-period comparison more meaningful. Carrying SOC can help or hurt under imperfect forecasts and finite-horizon terminal targets.","",
    "## Largest daily main-policy differences","",
    "These post-run examples illustrate accounting and boundary changes, not an additional strategy-selection rule.","",
    "| Market | Date | Main minus reset EUR | Main start SOC MWh | Main end SOC MWh |",
    "|---|---|---:|---:|---:|"]
    selected=[]
    for z,g in daily.groupby("zone"):
        a=g[g.policy=="continuous"].set_index("day_cet")
        b=g[g.policy=="daily_reset_fee_0"].set_index("day_cet")
        delta=a.net_margin_eur-b.net_margin_eur
        for day in dict.fromkeys([delta.idxmin(),delta.idxmax()]):
            r=a.loc[day];lines.append(f"| {z} | {day} | {delta.loc[day]:+.2f} | {r.start_soc_mwh:.3f} | {r.end_soc_mwh:.3f} |")
            selected.append(hourly[(hourly.zone==z)&(hourly.day_cet==day)&hourly.policy.isin(["continuous","daily_reset_fee_0"])])
    pd.concat(selected,ignore_index=True).to_csv(out/"continuous_case_dispatch_2025.csv",index=False)
    lines+=["","## Validation and limits","",
    "The zero-fee daily comparator reproduces all published seven-day daily results. Runtime checks enforce physical bounds, no simultaneous charging/discharging, SOC continuity, cutoff-history availability, unchanged prior commitments, ledger cashflow and full-period oracle dominance. Dedicated tests exercise two-day leakage protection, cutoff projection, analytical fees/settlement, DST and negative prices.","",
    "The forecast repeats one issuance-time hourly profile across both days, so extra horizon is not extra predictive information. Terminal assumptions can materially influence actions. This remains a price-taking backtest with perfect acceptance and execution, no imbalance exposure, no outages and no bid/ask order book. Fees are sensitivity assumptions. Results are simulated operating margin, not investment profit.","",
    "## Reproduce and inspect","",
    "- [Frozen protocol](../docs/continuous-operation-protocol.md) and [configuration](../config/continuous-operation.json).",
    "- [Audit](continuous_audit_2025.json), [metrics](continuous_metrics_2025.csv), [daily](continuous_daily_2025.csv), [monthly](continuous_monthly_2025.csv), [decision and projected-state audit](continuous_decisions_2025.csv), [selected hourly cases](continuous_case_dispatch_2025.csv).",
    "- [Compressed full dispatch and trade ledger](../data/continuous/README.md). Run python scripts/analyse_continuous.py with recovered price inputs and the recorded dependencies.",
    "- Source: Bundesnetzagentur | SMARD.de via Energy-Charts, CC BY 4.0, as documented in the input recovery audit.",
    "- Next: verify intraday data and execution assumptions before adding incremental trades against the preserved day-ahead positions.",""]
    (out/"continuous_results_2025.md").write_text("\n".join(lines))
    fig,axes=plt.subplots(2,2,figsize=(12,7),layout="constrained")
    for col,z in enumerate(["DE-LU","FR"]):
        g=daily[daily.zone==z]
        for name,color,label in [("daily_reset_fee_0","#64748b","Daily reset"),("continuous","#087f8c","Continuous")]:
            a=g[g.policy==name].sort_values("day_cet")
            dates=pd.to_datetime(a.day_cet)
            axes[0,col].plot(dates,a.net_margin_eur.cumsum()/1000,label=label,color=color)
            axes[1,col].plot(dates,a.end_soc_mwh,label=label,color=color,linewidth=1)
        axes[0,col].set_title(z);axes[0,col].set_ylabel("Cumulative net margin (thousand EUR)")
        axes[1,col].set_ylabel("Committed day-end SOC (MWh)")
        for ax in axes[:,col]:ax.legend();ax.grid(alpha=.2);ax.tick_params(axis="x",rotation=25)
    fig.suptitle("Continuous operation vs daily reset — 2025 retrospective comparison")
    fig.savefig(figdir/"continuous_2025.svg");plt.close(fig)
