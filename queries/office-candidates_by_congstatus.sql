/*
Author: Johanan Tai
Description: Queries office candidates (incumbents) by their legislative session.
*/


WITH local_var AS (
    SELECT %(start_date)s::DATE AS termstarts,
		   %(end_date)s::DATE AS termends
)

SELECT
    /*Due to a cartesian product from cross join, distinct is needed to prevent duplicates*/
    DISTINCT ON (candidate.candidate_id)
    candidate.candidate_id,
    candidate.firstname,
    candidate.nickname,
    candidate.middlename,
    candidate.lastname,
    candidate.suffix,
    office.name AS office,
    state.name AS state,
    state.state_id AS state_id,
    districtname.name AS district,
    party.name AS party

FROM office_candidate
JOIN candidate USING (candidate_id)

LEFT JOIN office USING (office_id)
LEFT JOIN state ON office_candidate.state_id = state.state_id
LEFT JOIN districtname USING (districtname_id)
LEFT JOIN office_candidate_party USING (office_candidate_id)
LEFT JOIN party ON office_candidate_party.party_id = party.party_id

JOIN congstatus_candidate USING (office_candidate_id)
JOIN congstatus ON congstatus_candidate.congstatus_id = congstatus.congstatus_id

CROSS JOIN local_var

/*
Other than termstart/termend, office id(s), office type(s) and state(s) 
are also considered for futher refinement.
*/
WHERE 
    congstatus.statusdate BETWEEN local_var.termstarts and local_var.termends
    
    AND office_candidate.office_id = ANY(%(office_ids)s)
    
    AND (office_candidate.state_id = ANY(%(state_ids)s)
            OR state.name = ANY(%(state_names)s)
        )

