"""Load cleaned CSVs into an in-memory SQLite database and run sql/queries.sql."""
import re, sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data" / "processed", ROOT / "outputs" / "sql_results"
RES.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(":memory:")
for t in ["vendors", "requisitions", "candidates", "stage_history"]:
    pd.read_csv(PROC / f"{t}.csv").to_sql(t, con, index=False)

text = (ROOT / "sql" / "queries.sql").read_text()
for name, body in re.findall(r"-- name: (\w+)\n(.*?)(?=\n-- name:|\Z)", text, flags=re.S):
    df = pd.read_sql_query(body, con)
    df.to_csv(RES / f"{name}.csv", index=False)
    print(f"\n=== {name} ===\n{df.to_string(index=False)}")
