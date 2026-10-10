"""Exploratory analysis of the hiring funnel with pandas, plus charts.

Run after clean_data.py. Outputs PNG charts to outputs/charts/ and the
tables used for the Power BI model to data/processed/.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, CH = ROOT / "data" / "processed", ROOT / "outputs" / "charts"
CH.mkdir(parents=True, exist_ok=True)
STAGES = ["Applied", "Screening", "Technical Interview", "Offer", "Joined"]
NAVY, GREY = "#1F3A5F", "#9AA5B1"

req = pd.read_csv(PROC / "requisitions.csv", parse_dates=["open_date"])
cand = pd.read_csv(PROC / "candidates.csv", parse_dates=["applied_date"])
hist = pd.read_csv(PROC / "stage_history.csv", parse_dates=["stage_date"])
vendors = pd.read_csv(PROC / "vendors.csv")

# ---------- 1. funnel ----------
rank = {s: i for i, s in enumerate(STAGES)}
cand["rank"] = cand["final_stage"].map(rank)
funnel = pd.Series({s: int((cand["rank"] >= i).sum()) for i, s in enumerate(STAGES)})
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(funnel.index[::-1], funnel.values[::-1], color=NAVY)
for y, v in enumerate(funnel.values[::-1]):
    ax.text(v + 20, y, f"{v:,} ({v / funnel.iloc[0]:.0%})", va="center", fontsize=9)
ax.set_title("Hiring funnel: candidates reaching each stage"); ax.set_xlim(0, funnel.max() * 1.25)
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(CH / "01_funnel.png", dpi=150); plt.close(fig)

# ---------- 2. time-to-fill vs SLA ----------
joins = hist[hist.stage == "Joined"].merge(cand[["candidate_id", "requisition_id"]], on="candidate_id")
first = joins.groupby("requisition_id")["stage_date"].min().rename("first_join")
ttf = req.merge(first, on="requisition_id")
ttf["time_to_fill"] = (ttf["first_join"] - ttf["open_date"]).dt.days
ttf["sla_breached"] = ttf["time_to_fill"] > ttf["sla_days"]
by_skill = ttf.groupby("skill_family").agg(avg_days=("time_to_fill", "mean"), filled=("requisition_id", "count"),
                                           breach_pct=("sla_breached", "mean")).sort_values("avg_days")
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(by_skill.index, by_skill["avg_days"], color=NAVY)
ax.axhline(ttf["sla_days"].mean(), color="#C0392B", ls="--", lw=1, label=f"Avg SLA ({ttf['sla_days'].mean():.0f} days)")
ax.set_ylabel("Avg time-to-fill (days)"); ax.set_title("Time-to-fill by skill family"); ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(CH / "02_time_to_fill.png", dpi=150); plt.close(fig)

# ---------- 3. vendor performance ----------
vp = cand.merge(vendors, on="vendor_id").groupby("vendor_name").agg(
    submissions=("candidate_id", "count"), joined=("final_stage", lambda s: (s == "Joined").sum()))
vp["join_rate"] = vp["joined"] / vp["submissions"]; vp = vp.sort_values("join_rate")
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(vp.index, vp["join_rate"] * 100, color=NAVY)
for y, v in enumerate(vp["join_rate"] * 100): ax.text(v + 0.2, y, f"{v:.1f}%", va="center", fontsize=9)
ax.set_xlabel("Submission-to-join rate (%)"); ax.set_title("Vendor performance")
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(CH / "03_vendor_performance.png", dpi=150); plt.close(fig)

# ---------- 4. monthly hires + naive forecast backtest ----------
m = joins.set_index("stage_date").resample("MS").size().rename("hires")
m = m.iloc[:-1]  # drop the final partial month
fc = m.rolling(3).mean().shift(1)  # forecast = mean of previous 3 months
bt = pd.DataFrame({"actual": m, "forecast": fc}).dropna()
mape = (abs(bt.actual - bt.forecast) / bt.actual).mean()
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(m.index, m.values, color=NAVY, marker="o", label="Actual hires")
ax.plot(bt.index, bt.forecast, color=GREY, ls="--", marker="o", label="3-month moving-average forecast")
ax.set_title(f"Monthly hires vs naive forecast (backtest MAPE {mape:.0%})"); ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(CH / "04_monthly_hires_forecast.png", dpi=150); plt.close(fig)

# ---------- export flat tables for Power BI ----------
ttf.to_csv(PROC / "powerbi_requisition_time_to_fill.csv", index=False)
bt.reset_index(names="month").to_csv(PROC / "powerbi_monthly_hires_forecast.csv", index=False)

summary = f"""Funnel: {funnel.iloc[0]:,} applied -> {funnel.iloc[-1]:,} joined ({funnel.iloc[-1]/funnel.iloc[0]:.1%})
Requisitions filled: {len(ttf)} of {len(req)} | avg time-to-fill {ttf.time_to_fill.mean():.1f} days | SLA breached {ttf.sla_breached.mean():.0%}
Best vendor: {vp.index[-1]} ({vp.join_rate.iloc[-1]:.1%}) | Weakest: {vp.index[0]} ({vp.join_rate.iloc[0]:.1%})
Naive 3-month moving-average forecast backtest MAPE: {mape:.0%} (a baseline to beat, not a finished model)"""
(ROOT / "outputs" / "summary.txt").write_text(summary + "\n"); print(summary)
