-- Hiring funnel analytics queries (SQLite syntax; also works in PostgreSQL with minor date-function changes).
-- Tables: requisitions, candidates, stage_history, vendors   (see schema.sql)

-- name: 01_funnel_conversion
-- Candidates reaching each stage, with stage-to-stage and overall conversion (window functions).
WITH stage_rank AS (
    SELECT 'Applied' AS stage, 1 AS rnk UNION ALL SELECT 'Screening', 2 UNION ALL
    SELECT 'Technical Interview', 3 UNION ALL SELECT 'Offer', 4 UNION ALL SELECT 'Joined', 5
),
cand_rank AS (
    SELECT c.candidate_id, s.rnk AS reached_rank
    FROM candidates c JOIN stage_rank s ON s.stage = c.final_stage
),
funnel AS (
    SELECT sr.rnk, sr.stage,
           COUNT(cr.candidate_id) AS candidates_reached
    FROM stage_rank sr
    LEFT JOIN cand_rank cr ON cr.reached_rank >= sr.rnk
    GROUP BY sr.rnk, sr.stage
)
SELECT stage, candidates_reached,
       ROUND(100.0 * candidates_reached / LAG(candidates_reached) OVER (ORDER BY rnk), 1) AS pct_of_previous_stage,
       ROUND(100.0 * candidates_reached / FIRST_VALUE(candidates_reached) OVER (ORDER BY rnk), 1) AS pct_of_applied
FROM funnel
ORDER BY rnk;

-- name: 02_time_to_fill_by_skill
-- Time-to-fill = days from requisition open to the FIRST candidate joining. Compared with SLA.
WITH first_join AS (
    SELECT c.requisition_id, MIN(h.stage_date) AS first_join_date
    FROM stage_history h JOIN candidates c ON c.candidate_id = h.candidate_id
    WHERE h.stage = 'Joined'
    GROUP BY c.requisition_id
),
req_ttf AS (
    SELECT r.requisition_id, r.skill_family, r.sla_days,
           CAST(julianday(f.first_join_date) - julianday(r.open_date) AS INTEGER) AS time_to_fill
    FROM requisitions r JOIN first_join f ON f.requisition_id = r.requisition_id
)
SELECT skill_family,
       COUNT(*)                                   AS filled_requisitions,
       ROUND(AVG(time_to_fill), 1)                AS avg_time_to_fill_days,
       MIN(time_to_fill)                          AS fastest_days,
       MAX(time_to_fill)                          AS slowest_days,
       ROUND(100.0 * SUM(time_to_fill > sla_days) / COUNT(*), 1) AS pct_sla_breached
FROM req_ttf
GROUP BY skill_family
ORDER BY avg_time_to_fill_days;

-- name: 03_vendor_performance_ranking
-- Vendor offer-to-join ratio, with RANK() window function.
WITH vendor_stats AS (
    SELECT v.vendor_name,
           COUNT(*) AS submissions,
           SUM(c.final_stage IN ('Offer','Joined')) AS offers,
           SUM(c.final_stage = 'Joined')            AS joined
    FROM candidates c JOIN vendors v ON v.vendor_id = c.vendor_id
    GROUP BY v.vendor_name
)
SELECT vendor_name, submissions, offers, joined,
       ROUND(100.0 * joined / submissions, 2) AS submission_to_join_pct,
       ROUND(100.0 * joined / offers, 1)      AS offer_to_join_pct,
       RANK() OVER (ORDER BY 1.0 * joined / submissions DESC) AS performance_rank
FROM vendor_stats
ORDER BY performance_rank;

-- name: 04_monthly_hires_trend
-- Monthly joins with running total and month-over-month change (LAG + running SUM).
WITH monthly AS (
    SELECT strftime('%Y-%m', stage_date) AS join_month, COUNT(*) AS hires
    FROM stage_history WHERE stage = 'Joined'
    GROUP BY join_month
)
SELECT join_month, hires,
       SUM(hires) OVER (ORDER BY join_month) AS cumulative_hires,
       hires - LAG(hires) OVER (ORDER BY join_month) AS mom_change
FROM monthly
ORDER BY join_month;

-- name: 05_slowest_stage_transition
-- Average days spent between consecutive stages (self-join through LEAD).
WITH ordered AS (
    SELECT candidate_id, stage, stage_date,
           LEAD(stage)      OVER (PARTITION BY candidate_id ORDER BY stage_date) AS next_stage,
           LEAD(stage_date) OVER (PARTITION BY candidate_id ORDER BY stage_date) AS next_date
    FROM stage_history
)
SELECT stage || ' -> ' || next_stage AS transition,
       COUNT(*) AS candidates,
       ROUND(AVG(julianday(next_date) - julianday(stage_date)), 1) AS avg_days
FROM ordered
WHERE next_stage IS NOT NULL
GROUP BY stage, next_stage
HAVING COUNT(*) >= 20   -- ignore rare transitions caused by removed bad records
ORDER BY avg_days DESC;

-- name: 06_source_effectiveness
-- Which candidate sources convert best to joins? Uses a subquery filter to ignore tiny sources.
SELECT source,
       COUNT(*) AS candidates,
       SUM(final_stage = 'Joined') AS joined,
       ROUND(100.0 * SUM(final_stage = 'Joined') / COUNT(*), 2) AS join_rate_pct
FROM candidates
GROUP BY source
HAVING COUNT(*) >= (SELECT 0.02 * COUNT(*) FROM candidates)
ORDER BY join_rate_pct DESC;
