"""Generate a synthetic recruitment dataset (no real company or candidate data).

Creates deliberately messy raw CSVs (case/whitespace issues, duplicates,
missing values, bad dates) so the cleaning step has real work to do.
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

STAGES = ["Applied", "Screening", "Technical Interview", "Offer", "Joined"]
SKILLS = {"Cloud": 0.25, "DevOps": 0.2, "Full Stack": 0.3, "Data": 0.15, "SAP": 0.1}
LOCATIONS = ["Bengaluru", "Hyderabad", "Pune", "Chennai", "Remote"]
SOURCES = ["Job Portal", "Referral", "Vendor", "LinkedIn", "Walk-in"]
# vendor -> (quality multiplier on stage conversion, avg delay days)
VENDORS = {"V01": ("Apex Staffing", 1.15, 3), "V02": ("BrightHire", 1.00, 4),
           "V03": ("CoreTalent", 0.90, 5), "V04": ("DeltaResources", 1.05, 3),
           "V05": ("EdgeWorkforce", 0.80, 7)}
BASE_CONV = [0.60, 0.50, 0.32, 0.78]  # Applied->Screen->Tech->Offer->Joined

# ---- requisitions ----
n_req = 150
open_dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(RNG.integers(0, 330, n_req), unit="D")
skills = RNG.choice(list(SKILLS), n_req, p=list(SKILLS.values()))
req = pd.DataFrame({
    "requisition_id": [f"REQ{1000+i}" for i in range(n_req)],
    "role": [f"{s} Engineer" for s in skills],
    "skill_family": skills,
    "location": RNG.choice(LOCATIONS, n_req),
    "open_date": open_dates,
    "sla_days": RNG.choice([30, 35, 40, 45], n_req),
})

# ---- candidates + stage history ----
cand_rows, hist_rows, cid = [], [], 1
for _, r in req.iterrows():
    for _ in range(int(RNG.integers(8, 28))):
        v = RNG.choice(list(VENDORS), p=[.25, .25, .2, .15, .15])
        q, delay = VENDORS[v][1], VENDORS[v][2]
        src = "Vendor" if RNG.random() < 0.7 else RNG.choice(SOURCES)
        d = r.open_date + pd.Timedelta(days=int(RNG.integers(1, 30 + delay)))
        cand_id = f"C{cid:05d}"; cid += 1
        reached = 0
        hist_rows.append((cand_id, "Applied", d))
        for k, p in enumerate(BASE_CONV):
            if RNG.random() < min(p * q, 0.95):
                reached = k + 1
                d = d + pd.Timedelta(days=int(RNG.integers(2, 9 + delay)))
                hist_rows.append((cand_id, STAGES[reached], d))
            else:
                break
        cand_rows.append((cand_id, r.requisition_id, v, src, None, STAGES[reached]))
cand = pd.DataFrame(cand_rows, columns=["candidate_id", "requisition_id", "vendor_id", "source", "applied_date", "final_stage"])
hist = pd.DataFrame(hist_rows, columns=["candidate_id", "stage", "stage_date"])
cand["applied_date"] = cand["candidate_id"].map(hist[hist.stage == "Applied"].set_index("candidate_id")["stage_date"])
vendors = pd.DataFrame([(k, v[0]) for k, v in VENDORS.items()], columns=["vendor_id", "vendor_name"])

# ---- inject realistic mess into raw files ----
cand.loc[RNG.choice(cand.index, 60, replace=False), "source"] = None
cand.loc[RNG.choice(cand.index, 80, replace=False), "source"] = cand["source"].str.lower()
cand.loc[RNG.choice(cand.index, 50, replace=False), "source"] = " " + cand["source"].astype(str) + " "
cand = pd.concat([cand, cand.sample(40, random_state=1)], ignore_index=True)  # duplicate rows
req["location"] = req["location"].where(RNG.random(n_req) > 0.05, req["location"].str.upper())
hist = pd.concat([hist, hist.sample(30, random_state=2)], ignore_index=True)
hist_bad = hist[hist.stage == "Screening"].sample(15, random_state=3).index  # stage dated before applied
hist["stage_date"] = hist["stage_date"].dt.strftime("%Y-%m-%d")
hist.loc[hist_bad, "stage_date"] = "2024-12-15"

req.assign(open_date=req.open_date.dt.strftime("%Y-%m-%d")).to_csv(OUT / "requisitions.csv", index=False)
cand.assign(applied_date=cand.applied_date.dt.strftime("%Y-%m-%d")).to_csv(OUT / "candidates.csv", index=False)
hist.to_csv(OUT / "stage_history.csv", index=False)
vendors.to_csv(OUT / "vendors.csv", index=False)
print(f"requisitions={len(req)} candidates={len(cand)} stage_events={len(hist)} vendors={len(vendors)}")
