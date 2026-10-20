"""Post-test diagnosis only. Read unchanged hourly schedules; never refit/reoptimise."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

def run():
    path = ROOT / "data/processed/independent_dispatch_2025.csv"
    if not path.exists():
        raise SystemExit("Missing original hourly dispatch file. Recover it or reproduce the frozen evaluation first; daily aggregates cannot reconstruct hourly decisions.")
    h = pd.read_csv(path)
    h["timestamp_utc"] = pd.to_datetime(h.timestamp_utc, utc=True)
    daily = pd.read_csv(ROOT / "reports/independent_daily_2025.csv")
    cases = pd.read_csv(ROOT / "reports/ml_diagnosis_cases_2025.csv")
    selection = json.loads((ROOT / "reports/ml_selection_2024.json").read_text())
    output = ROOT / "reports"
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    differences, selected = [], []
    for zone in ("DE-LU", "FR"):
        forest = selection[zone]["family_winners"]["random_forest"]
        names = ["seven_day_same_hour", forest]
        s = h[(h.zone == zone) & h.model.isin(names)].copy()
        assert len(s) == 2 * 6359
        assert not s.duplicated(["model", "timestamp_utc"]).any()
        assert (s.day_cet == s.timestamp_utc.dt.tz_convert("Europe/Berlin").dt.strftime("%Y-%m-%d")).all()
        columns = ["actual_eur_mwh", "forecast_eur_mwh", "charge_mw", "discharge_mw", "soc_start_mwh", "soc_end_mwh", "gross_margin_eur", "degradation_eur", "net_margin_eur"]
        assert np.isfinite(s[columns].to_numpy()).all()
        # Frozen experiment is hourly; never silently apply this accounting to another resolution.
        for name in names:
            g = s[s.model == name].sort_values("timestamp_utc")
            expected = pd.date_range("2025-01-09", "2025-10-01", freq="h", inclusive="left", tz="Europe/Berlin").tz_convert("UTC")
            assert pd.DatetimeIndex(g.timestamp_utc).equals(expected)
            c, d = g.charge_mw.to_numpy(), g.discharge_mw.to_numpy()
            assert (c >= -1e-7).all() and (c <= 1+1e-7).all()
            assert (d >= -1e-7).all() and (d <= 1+1e-7).all()
            assert (np.minimum(c, d) < 1e-7).all()
            assert (g[["soc_start_mwh","soc_end_mwh"]].to_numpy() >= -1e-7).all()
            assert (g[["soc_start_mwh","soc_end_mwh"]].to_numpy() <= 2+1e-7).all()
            np.testing.assert_allclose(g.soc_end_mwh, g.soc_start_mwh + np.sqrt(.9)*c - d/np.sqrt(.9), atol=1e-6)
            for _, day in g.groupby("day_cet"):
                np.testing.assert_allclose([day.soc_start_mwh.iloc[0],day.soc_end_mwh.iloc[-1]], [1,1], atol=1e-6)
                np.testing.assert_allclose(day.soc_start_mwh.iloc[1:],day.soc_end_mwh.iloc[:-1],atol=1e-6)
        s["sales_eur"] = s.actual_eur_mwh * s.discharge_mw
        s["purchases_eur"] = s.actual_eur_mwh * s.charge_mw
        np.testing.assert_allclose(s.gross_margin_eur, s.sales_eur-s.purchases_eur, atol=1e-6)
        np.testing.assert_allclose(s.degradation_eur, 10*s.discharge_mw, atol=1e-6)
        np.testing.assert_allclose(s.net_margin_eur, s.sales_eur-s.purchases_eur-s.degradation_eur, atol=1e-6)
        grouped = s.groupby(["model", "day_cet"])[["sales_eur","purchases_eur","gross_margin_eur","degradation_eur","net_margin_eur","discharge_mw"]].sum()
        reference = daily[(daily.zone==zone)&daily.model.isin(names)].set_index(["model","day_cet"]).sort_index()
        assert grouped.index.equals(reference.index)
        for col in ["gross_margin_eur","degradation_eur","net_margin_eur"]:
            np.testing.assert_allclose(grouped[col],reference[col],atol=1e-5,rtol=0)
        np.testing.assert_allclose(grouped.discharge_mw,reference.discharged_mwh,atol=1e-5,rtol=0)
        delta = grouped.loc[forest] - grouped.loc[names[0]]
        for day, row in delta.iterrows():
            differences.append({"zone":zone,"day_cet":day,**row.to_dict()})
        for case in cases[cases.zone==zone].itertuples():
            subset = s[s.day_cet==case.day_cet].sort_values(["model","timestamp_utc"])
            selected.append(subset)
            fig, axes = plt.subplots(4,1,figsize=(11,10),sharex=True,layout="constrained")
            baseline = subset[subset.model==names[0]].sort_values("timestamp_utc")
            rf = subset[subset.model==forest].sort_values("timestamp_utc")
            assert baseline.timestamp_utc.tolist()==rf.timestamp_utc.tolist()
            np.testing.assert_allclose(baseline.actual_eur_mwh,rf.actual_eur_mwh,atol=0,rtol=0)
            x = np.arange(len(baseline))
            axes[0].plot(x,baseline.actual_eur_mwh,color="black",label="Actual")
            for name,color,label in [(names[0],"#157f79","Seven-day"),(forest,"#bd6038","RF")]:
                g = subset[subset.model==name].sort_values("timestamp_utc")
                axes[0].plot(x,g.forecast_eur_mwh,color=color,linestyle="--",label=label+" forecast")
                axes[1].step(x,g.charge_mw,where="post",color=color,label=label)
                axes[2].step(x,g.discharge_mw,where="post",color=color,label=label)
                axes[3].plot(np.arange(len(g)+1),np.r_[g.soc_start_mwh.to_numpy(),g.soc_end_mwh.iloc[-1]],color=color,label=label)
            for ax,y in zip(axes,["Price (EUR/MWh)","Charge (MW)","Discharge (MW)","SOC (MWh)"]):
                ax.set_ylabel(y);ax.grid(alpha=.2);ax.legend(loc="best")
            ticks=np.arange(0,len(baseline),3)
            axes[3].set_xticks(ticks,baseline.timestamp_utc.dt.tz_convert("Europe/Berlin").dt.strftime("%H:%M").iloc[ticks])
            axes[3].set_xlabel("Local delivery time (Europe/Berlin); SOC includes final boundary")
            fig.suptitle(f"{zone} {case.day_cet}: RF minus seven-day EUR{case.net_difference_eur:.2f}")
            fig.savefig(figures/f"ml_diagnosis_{zone}_{case.day_cet}.svg");plt.close(fig)
    frame = pd.DataFrame(differences)
    np.testing.assert_allclose(frame.net_margin_eur,frame.sales_eur-frame.purchases_eur-frame.degradation_eur,atol=1e-5)
    frame.to_csv(output/"ml_diagnosis_hourly_reconciled_daily_2025.csv",index=False)
    frame.groupby("zone").sum(numeric_only=True).to_csv(output/"ml_diagnosis_sales_purchase_totals_2025.csv")
    pd.concat(selected,ignore_index=True).to_csv(output/"ml_diagnosis_selected_dispatch_2025.csv",index=False)
    print("Hourly accounting and 16 case charts completed; all reconciliation checks passed.")

if __name__ == "__main__":
    run()
