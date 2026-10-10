# Power BI data model (star schema)

Load the cleaned CSVs from `data/processed/` with **Get Data > Text/CSV**, then in Power Query set data types
(dates as Date, IDs as Text).

| Table | Type | Key | Notes |
|---|---|---|---|
| `candidates` | Fact | `candidate_id` | one row per candidate, has `final_stage`, `vendor_id`, `requisition_id` |
| `stage_history` | Fact | `candidate_id` + `stage` | one row per stage event |
| `requisitions` | Dimension | `requisition_id` | skill family, location, SLA days |
| `vendors` | Dimension | `vendor_id` | vendor name |
| `Date` | Dimension | `Date` | create with `CALENDAR(DATE(2025,1,1), DATE(2026,3,31))` |

Relationships (all many-to-one, single direction):
`candidates[requisition_id] -> requisitions`, `candidates[vendor_id] -> vendors`,
`stage_history[candidate_id] -> candidates`, `stage_history[stage_date] -> Date[Date]`.

Suggested pages: **Funnel** (funnel chart + conversion cards), **Speed** (time-to-fill by skill vs SLA),
**Vendors** (join rate ranking), **Trend** (monthly hires with MTD/QTD/YTD cards).
