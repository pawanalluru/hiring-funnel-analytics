# DAX measures

```DAX
Candidates Applied = DISTINCTCOUNT ( candidates[candidate_id] )

Candidates Joined =
CALCULATE ( DISTINCTCOUNT ( candidates[candidate_id] ), candidates[final_stage] = "Joined" )

Candidates Offered =
CALCULATE ( DISTINCTCOUNT ( candidates[candidate_id] ),
            candidates[final_stage] IN { "Offer", "Joined" } )

Offer to Join % = DIVIDE ( [Candidates Joined], [Candidates Offered] )

Submission to Join % = DIVIDE ( [Candidates Joined], [Candidates Applied] )

Hires =
CALCULATE ( DISTINCTCOUNT ( stage_history[candidate_id] ), stage_history[stage] = "Joined" )

Hires MTD = TOTALMTD ( [Hires], 'Date'[Date] )
Hires QTD = TOTALQTD ( [Hires], 'Date'[Date] )
Hires YTD = TOTALYTD ( [Hires], 'Date'[Date] )

Hires MoM Change =
VAR prev = CALCULATE ( [Hires], DATEADD ( 'Date'[Date], -1, MONTH ) )
RETURN [Hires] - prev

Avg Time to Fill (days) = AVERAGE ( powerbi_requisition_time_to_fill[time_to_fill] )

SLA Breach % =
DIVIDE ( COUNTROWS ( FILTER ( powerbi_requisition_time_to_fill,
                              powerbi_requisition_time_to_fill[sla_breached] = TRUE () ) ),
         COUNTROWS ( powerbi_requisition_time_to_fill ) )
```
Load `powerbi_requisition_time_to_fill.csv` as an extra table for the last two measures.
