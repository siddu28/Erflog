from agents.agent_3_strategist.graph import get_interview_gap_analysis

def fetch_interview_context(user_id: str, job_id: str):
    agent3_result = get_interview_gap_analysis(
        job_id=str(job_id),
        user_id=str(user_id)
    )
    
    job_data = agent3_result.get("job", {})
    user_data = agent3_result.get("user", {})
    gap_analysis = agent3_result.get("gap_analysis", {})
    similarity_score = agent3_result.get("similarity_score", 0.0)
    
    gap_report = {
        "status": "gap_detected" if gap_analysis.get("missing_skills") else "ready",
        "similarity_score": similarity_score,
        "match_tier": gap_analysis.get("match_tier", "B"),
        "missing_skills": gap_analysis.get("missing_skills", []),
        "weak_areas": gap_analysis.get("weak_areas", []),
        "suggested_questions": gap_analysis.get("suggested_questions", []),
        "assessment": gap_analysis.get("assessment", "")
    }

    return {
        "job": job_data,
        "user": user_data,
        "gaps": gap_report
    }
