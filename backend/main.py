"""
Career Flow AI - Main Application Entry Point
FastAPI Server for Agentic AI Backend with Multi-Agent Workflow
"""

import os
import uuid
from typing import Optional, Dict
from dotenv import load_dotenv

# Load env FIRST before any other imports
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import auth dependency
from auth.dependencies import get_current_user

# --- IMPORTS FOR AGENTS & DB ---
from core.state import AgentState
from core.db import db_manager  # Database connection

# Import routers (The decoupled way)
from agents.agent_1_perception.router import router as agent1_router 
from agents.agent_4_operative import agent4_router

# Import Agent Nodes/Functions (Only for agents NOT yet decoupled)
from agents.agent_2_market.graph import market_scan_node
from agents.agent_3_strategist.graph import search_jobs as strategist_search_jobs, process_career_strategy
from agents.agent_6_chat_interview.graph import run_interview_turn

app = FastAPI(
    title="Career Flow AI API",
    description="AI-powered career automation system with Multi-Agent Workflow",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent1_router) # Mounts /api/perception/*
app.include_router(agent4_router)

# -----------------------------------------------------------------------------
# Global Session Store
# -----------------------------------------------------------------------------
SESSIONS: Dict[str, AgentState] = {}

# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    query: Optional[str] = None
    context: Optional[dict] = None

class SearchRequest(BaseModel):
    query: str

class KitRequest(BaseModel):
    user_name: str
    job_title: str
    job_company: str
    session_id: Optional[str] = None 
    job_description: Optional[str] = None 

class SessionRequest(BaseModel):
    session_id: str

class MarketScanRequest(BaseModel):
    session_id: str

class StrategyRequest(BaseModel):
    query: str 

class ApplicationRequest(BaseModel):
    session_id: str
    job_description: Optional[str] = None

class InterviewRequest(BaseModel):
    session_id: str         
    user_message: str = ""  
    job_context: str        

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def get_session(session_id: str) -> AgentState:
    """Retrieve session state or raise 404."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return SESSIONS[session_id]


def initialize_state() -> AgentState:
    """Create a fresh AgentState with default values."""
    return AgentState(
        resume_text=None,
        skills=[],
        user_id=None,
        context={},
        results={}
    )

# -----------------------------------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "Career Flow AI API Online",
        "version": "2.0.0",
        "agents_active": 6,
        "endpoints": {
            # Updated to show the new Perception endpoints
            "perception": [
                "/api/perception/upload-resume", 
                "/api/perception/sync-github", 
                "/api/perception/onboarding", 
                "/api/perception/watchdog/check", 
                "/api/perception/verify/quiz", 
                "/api/perception/profile"
            ],
            "workflow": ["/api/init", "/api/market-scan", "/api/generate-strategy", "/api/generate-application"],
            "interview": "/api/interview/chat",
            "legacy": ["/api/match", "/api/generate-kit"],
            "agent4": "/agent4",
            "auth": "/api/me"
        }
    }


@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    """
    Protected endpoint - returns current user info from JWT.
    Requires valid Supabase JWT in Authorization header.
    """
    return {
        "user_id": user["sub"],
        "email": user.get("email"),
        "provider": user.get("app_metadata", {}).get("provider")
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "Career Flow AI Backend is running",
            "active_sessions": len(SESSIONS)
        }
    )


@app.post("/analyze")
async def analyze_career(request: AnalyzeRequest):
    """Legacy analyze endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Analysis request received",
            "data": {}
        }
    )


@app.post("/api/match")
async def match_agent(request: SearchRequest):
    """Match agent endpoint - uses Agent 3 Strategist."""
    if not request.query:
        raise HTTPException(status_code=400, detail="Query text is required")
    
    try:
        result = process_career_strategy(request.query)
        return {
            "status": "success",
            "count": result.get("matches_found", 0),
            "matches": result.get("strategy_report", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match agent error: {str(e)}")


@app.post("/api/generate-kit")
async def generate_kit_endpoint(request: KitRequest):
    """
    Generate deployment kit - tailored resume PDF for a specific job.
    Uses Agent 4 (Operative) to mutate the resume.
    """
    print(f"[Generate Kit] Request for: {request.user_name} - {request.job_title} @ {request.job_company}")
    
    # Try to get user_id from session
    user_id = None
    user_profile = None
    
    if request.session_id and request.session_id in SESSIONS:
        state = SESSIONS[request.session_id]
        user_id = state.get("user_id")
        perception_results = state.get("results", {}).get("perception", {})
        user_profile = {
            "name": perception_results.get("name") or request.user_name,
            "email": perception_results.get("email", ""),
            "skills": state.get("skills", []),
            "experience_summary": perception_results.get("experience_summary", ""),
            "education": perception_results.get("education", ""),
            "resume": perception_results.get("resume_json", {}),
            "user_id": user_id 
        }
        print(f"[Generate Kit] Found user_id from session: {user_id}")
    
    # If no session, try to find most recent profile from DB
    if not user_id:
        try:
            supabase = db_manager.get_client()
            response = supabase.table("profiles").select("*").order("created_at", desc=True).limit(1).execute()
            
            if response.data:
                profile = response.data[0]
                user_id = profile.get("user_id") 
                user_profile = {
                    "name": profile.get("name") or request.user_name,
                    "email": profile.get("email", ""),
                    "skills": profile.get("skills", []),
                    "experience_summary": profile.get("experience_summary", ""),
                    "education": profile.get("education", ""),
                    "resume": profile.get("resume_json", {}),
                    "user_id": user_id 
                }
                print(f"[Generate Kit] Found user_id from DB: {user_id}")
                print(f"[Generate Kit] Resume URL in DB: {profile.get('resume_url', 'N/A')}")
        except Exception as e:
            print(f"[Generate Kit] DB lookup failed: {e}")
    
    if not user_id:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "No user profile found. Please upload your resume first.",
                "detail": "Upload your resume on the home page to enable resume generation."
            }
        )
    
    # Build job description from request
    job_description = request.job_description or f"""
    {request.job_title} at {request.job_company}
    
    We are looking for a talented {request.job_title} to join our team at {request.job_company}.
    """
    
    try:
        # Run Agent 4 to generate the tailored resume
        print(f"[Generate Kit] Running Agent 4 for user: {user_id}")
        print(f"[Generate Kit] Will download PDF: {user_id}.pdf from storage")
        
        from agents.agent_4_operative.graph import run_agent4
        
        operative_result = run_agent4(job_description, user_profile)
        
        pdf_url = operative_result.get("pdf_url")
        pdf_path = operative_result.get("pdf_path")
        
        print(f"[Generate Kit] ✅ Resume generated!")
        print(f"   PDF URL: {pdf_url}")
        
        if pdf_url:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Resume generated successfully",
                    "data": {
                        "pdf_url": pdf_url,
                        "pdf_path": pdf_path,
                        "user_name": request.user_name,
                        "job_title": request.job_title,
                        "job_company": request.job_company,
                        "application_status": operative_result.get("application_status", "ready")
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to generate PDF",
                    "detail": str(operative_result.get("error", "Unknown error"))
                }
            )
            
    except Exception as e:
        print(f"[Generate Kit] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Failed to generate resume: {str(e)}"
            }
        )

# -----------------------------------------------------------------------------
# NEW AGENT WORKFLOW ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/api/init")
async def init_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = initialize_state()
    print(f"[Orchestrator] New session initialized: {session_id}")
    return {"status": "success", "session_id": session_id, "message": "Session initialized."}


# NOTE: /api/watchdog/check REMOVED. Use /api/perception/watchdog/check instead.


@app.post("/api/market-scan")
async def market_scan(request: MarketScanRequest):
    """Run Agent 2 (Market Sentinel) to find job matches."""
    session_id = request.session_id
    state = get_session(session_id)
    try:
        print(f"[Orchestrator] Running Agent 2 (Market) for session: {session_id}")
        updated_state = market_scan_node(state)
        SESSIONS[session_id].update(updated_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market Agent failed: {str(e)}")
    market_results = SESSIONS[session_id].get("results", {}).get("market", {})
    job_matches = market_results.get("job_matches", [])
    return {"status": "success", "session_id": session_id, "job_matches": job_matches, "total_matches": len(job_matches)}


@app.post("/api/generate-strategy")
async def generate_strategy(request: StrategyRequest):
    """Run Agent 3 (Strategist) for semantic job matching with roadmaps."""
    query_text = request.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query is required for job matching.")
    try:
        print(f"[Orchestrator] Running Agent 3 (Strategist) with query: {query_text[:100]}...")
        result = process_career_strategy(query_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategist Agent failed: {str(e)}")
    
    return {
        "status": "success",
        "strategy": {
            "matched_jobs": result.get("strategy_report", []),
            "total_matches": result.get("matches_found", 0),
            "query_used": query_text[:200],
            "tier_summary": {
                "A_ready": len([j for j in result.get("strategy_report", []) if j.get("tier") == "A"]),
                "B_roadmap": len([j for j in result.get("strategy_report", []) if j.get("tier") == "B"]),
                "C_low": len([j for j in result.get("strategy_report", []) if j.get("tier") == "C"])
            }
        }
    }


@app.post("/api/generate-application")
async def generate_application(request: ApplicationRequest):
    """Run Agent 4 (Operative) to generate tailored resume and outreach."""
    session_id = request.session_id
    state = get_session(session_id)
    job_description = request.job_description
    if not job_description:
        strategist_results = state.get("results", {}).get("strategist", {})
        matched_jobs = strategist_results.get("matched_jobs", [])
        if matched_jobs: job_description = matched_jobs[0].get("description", "")
    if not job_description:
        market_results = state.get("results", {}).get("market", {})
        job_matches = market_results.get("job_matches", [])
        if job_matches: job_description = job_matches[0].get("description", job_matches[0].get("summary", ""))
    if not job_description:
        raise HTTPException(status_code=400, detail="job_description is required")
    
    perception_results = state.get("results", {}).get("perception", {})
    user_profile = {
        "name": perception_results.get("name"),
        "email": perception_results.get("email"),
        "skills": state.get("skills", []),
        "experience_summary": perception_results.get("experience_summary"),
        "education": perception_results.get("education"),
        "resume": perception_results.get("resume_json", {})
    }
    
    try:
        print(f"[Orchestrator] Running Agent 4 (Operative) for session: {session_id}")
        from agents.agent_4_operative.graph import run_agent4
        operative_result = run_agent4(job_description, user_profile)
        if "results" not in SESSIONS[session_id]: SESSIONS[session_id]["results"] = {}
        SESSIONS[session_id]["results"]["operative"] = operative_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operative Agent failed: {str(e)}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "application": {
            "pdf_path": operative_result.get("pdf_path"),
            "pdf_url": operative_result.get("pdf_url"),
            "recruiter_email": operative_result.get("recruiter_email"),
            "application_status": operative_result.get("application_status"),            
            "rewritten_content": operative_result.get("rewritten_content")
        }
    }


@app.post("/api/interview/chat")
async def interview_chat(request: InterviewRequest):
    """Agent 6: Interview Chat Endpoint"""
    if not request.session_id: raise HTTPException(status_code=400, detail="session_id is required")
    if not request.job_context: raise HTTPException(status_code=400, detail="job_context is required")
    try:
        result = run_interview_turn(session_id=request.session_id, user_message=request.user_message, job_context=request.job_context)
        return {"status": "success", "response": result["response"], "stage": result["stage"], "message_count": result["message_count"]}
    except Exception as e:
        print(f"❌ Interview Error: {e}")
        raise HTTPException(status_code=500, detail=f"Interview agent error: {str(e)}")

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")