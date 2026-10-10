-- Reference schema (the Python runner loads the cleaned CSVs into an in-memory SQLite DB with these tables).
CREATE TABLE vendors       (vendor_id TEXT PRIMARY KEY, vendor_name TEXT);
CREATE TABLE requisitions  (requisition_id TEXT PRIMARY KEY, role TEXT, skill_family TEXT,
                            location TEXT, open_date DATE, sla_days INTEGER);
CREATE TABLE candidates    (candidate_id TEXT PRIMARY KEY, requisition_id TEXT REFERENCES requisitions,
                            vendor_id TEXT REFERENCES vendors, source TEXT,
                            applied_date DATE, final_stage TEXT);
CREATE TABLE stage_history (candidate_id TEXT REFERENCES candidates, stage TEXT, stage_date DATE);
