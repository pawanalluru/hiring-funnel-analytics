"""Clean and validate the raw recruitment CSVs with pandas.

Every fix is logged so the data-quality changes are transparent.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
log = []

req = pd.read_csv(RAW / "requisitions.csv", parse_dates=["open_date"])
cand = pd.read_csv(RAW / "candidates.csv", parse_dates=["applied_date"])
hist = pd.read_csv(RAW / "stage_history.csv", parse_dates=["stage_date"])
vendors = pd.read_csv(RAW / "vendors.csv")

# 1. standardise text
req["location"] = req["location"].str.strip().str.title()
cand["source"] = cand["source"].str.strip().str.title().replace({"Linkedin": "LinkedIn", "Walk-In": "Walk-in"})
log.append(f"Standardised text casing/whitespace (e.g. unique sources now: {sorted(cand['source'].dropna().unique())})")

# 2. missing values
n_missing = cand["source"].isna().sum()
cand["source"] = cand["source"].fillna("Unknown")
log.append(f"Filled {n_missing} missing candidate sources with 'Unknown'")

# 3. duplicates
before = len(cand); cand = cand.drop_duplicates(); log.append(f"Removed {before - len(cand)} duplicate candidate rows")
before = len(hist); hist = hist.drop_duplicates(); log.append(f"Removed {before - len(hist)} duplicate stage events")

# 4. validate dates: a stage cannot happen before the candidate applied
hist = hist.merge(cand[["candidate_id", "applied_date"]], on="candidate_id", how="inner")
bad = hist["stage_date"] < hist["applied_date"]
log.append(f"Dropped {bad.sum()} stage events dated before the application date")
hist = hist[~bad].drop(columns="applied_date")

# 5. referential integrity
orphan = ~cand["requisition_id"].isin(req["requisition_id"]); assert not orphan.any()
log.append("Referential integrity check passed (all candidates map to a requisition)")

req.to_csv(OUT / "requisitions.csv", index=False)
cand.to_csv(OUT / "candidates.csv", index=False)
hist.to_csv(OUT / "stage_history.csv", index=False)
vendors.to_csv(OUT / "vendors.csv", index=False)
(ROOT / "outputs" / "data_quality_log.txt").write_text("\n".join(log) + "\n")
print("\n".join(log))
