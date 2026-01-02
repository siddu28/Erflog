import os
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


"""
Agent 4 Service - Resume Mutation Service
"""

from .tools import mutate_resume_for_job, save_application_to_db


def generate_resume(user_id: str = None, job_description: str = None, job_id: str | int = None, **kwargs) -> dict:
    """
    Main service function to generate/mutate a resume for a job.
    
    Args:
        user_id: User's UUID (required).
        job_description: Target job description (required).
        job_id: Optional Job ID to link application in DB.
    
    Returns:
        Dict with pdf_url, changes_made, etc.
    """
    if not user_id:
        return {
            "status": "error",
            "error": "user_id is required",
            "message": "Please provide a user_id."
        }
    
    if not job_description:
        return {
            "status": "error", 
            "error": "job_description is required",
            "message": "Please provide a job description."
        }
    
    # Use the new mutation flow
    result = mutate_resume_for_job(user_id, job_description)
    
    # Add additional fields for API response compatibility
    result["application_status"] = "ready" if result.get("status") == "success" else "failed"
    result["optimized_resume"] = {
        "changes": result.get("replacements", []),
        "keywords": result.get("keywords_added", [])
    }
    
    # Save to DB if job_id is present and result was successful
    if job_id and result.get("status") == "success":
        try:
            # Ensure job_id is int (schema says int8)
            job_id_int = int(job_id)
            
            save_application_to_db(
                user_id=user_id,
                job_id=job_id_int,
                tailored_resume_url=result.get("pdf_url"),
                custom_responses=result.get("optimized_resume")
            )
        except Exception as e:
            print(f"⚠️ [Agent 4] Failed to save application to DB: {e}")
            # Don't fail the whole request if DB save fails
            
    return result


# Singleton instance
class Agent4Service:
    """
    Service layer for Agent 4 - Application Operative.
    Handles all business logic and orchestrates the workflow.
    """
    
    def __init__(self):
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of dependencies."""
        if not self._initialized:
            from .graph import app
            from .tools import (
                fetch_user_profile_by_uuid,
                fetch_user_profile,
                build_resume_from_profile,
                rewrite_resume_content,
                find_recruiter_email,
                generate_application_responses
            )
            from .pdf_engine import generate_pdf
            
            self.app = app
            self.fetch_user_profile_by_uuid = fetch_user_profile_by_uuid
            self.fetch_user_profile = fetch_user_profile
            self.build_resume_from_profile = build_resume_from_profile
            self.rewrite_resume_content = rewrite_resume_content
            self.find_recruiter_email = find_recruiter_email
            self.generate_pdf = generate_pdf
            self.generate_application_responses = generate_application_responses
            
            self._initialized = True
    
    def generate_resume(
        self,
        user_id: str,
        job_description: str,
        job_id: Optional[str] = None
    ) -> dict:
        """
        Generate an optimized resume for a user targeting a specific job.
        
        Args:
            user_id: UUID of the user from Supabase.
            job_description: Target job description.
            job_id: Optional job ID for tracking.
        
        Returns:
            Dictionary with optimized resume, PDF path, and metadata.
        """
        self._ensure_initialized()
        start_time = time.time()
        
        # 1. Fetch user profile from Supabase
        profile = self.fetch_user_profile_by_uuid(user_id)
        user_profile = self.build_resume_from_profile(profile)
        
        # Add user_id to profile for file naming
        user_profile["user_id"] = user_id
        
        # 2. Run the Agent 4 workflow
        from .state import Agent4State
        
        initial_state: Agent4State = {
            "job_description": job_description,
            "user_profile": user_profile,
            "rewritten_content": {},
            "pdf_path": "",
            "pdf_url": "",
            "recruiter_email": "",
            "application_status": "pending",
            "feedback_loop": {}
        }
        
        result = self.app.invoke(initial_state)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "user_id": user_id,
            "original_profile": user_profile,
            "optimized_resume": result.get("rewritten_content", {}),
            "pdf_path": result.get("pdf_path", ""),
            "pdf_url": result.get("pdf_url", ""),
            "recruiter_email": result.get("recruiter_email"),
            "application_status": result.get("application_status", "pending"),
            "processing_time_ms": processing_time,
            "message": "Resume generated successfully"
        }
    
    def generate_resume_by_profile_id(
        self,
        profile_id: int,
        job_description: str
    ) -> dict:
        """
        Generate resume using profile ID instead of UUID.
        Note: In new schema, profile_id IS the user_id (uuid).
        This method now expects user_id directly.
        """
        self._ensure_initialized()
        
        # In the new schema, profiles.user_id is the primary key
        # So profile_id should actually be a user_id (uuid string)
        # For backward compatibility, try to look it up
        from core.db import db_manager
        supabase = db_manager.get_client()
        
        # Try to find by user_id directly (new schema)
        response = supabase.table("profiles").select("user_id").eq("user_id", str(profile_id)).execute()
        
        if response.data:
            user_id = response.data[0]["user_id"]
            return self.generate_resume(user_id, job_description)
        
        # If not found, the profile_id might be invalid
        raise ValueError(f"Profile with user_id {profile_id} not found")
    
    def analyze_rejection(
        self,
        user_id: str,
        job_description: str,
        rejection_reason: Optional[str] = None
    ) -> dict:
        """
        Analyze why a resume was rejected and update learning.
        """
        self._ensure_initialized()
        
        from .evolution import analyze_rejection, update_vector_memory
        
        # Fetch user profile
        profile = self.fetch_user_profile_by_uuid(user_id)
        user_profile = self.build_resume_from_profile(profile)
        
        # Analyze the rejection
        gap_analysis = analyze_rejection(job_description, user_profile)
        
        # Update vector memory with anti-pattern
        memory_result = update_vector_memory(user_id, gap_analysis)
        
        # Extract recommendations
        recommendations = [
            line.strip() 
            for line in gap_analysis.split('\n') 
            if line.strip() and not line.startswith('#')
        ][:5]
        
        return {
            "success": True,
            "user_id": user_id,
            "gap_analysis": gap_analysis,
            "recommendations": recommendations,
            "anti_pattern_created": memory_result.get("anti_pattern_created", False)
        }
    
    def get_pdf_url(self, pdf_path: str) -> str:
        """
        Get the URL/path to access a generated PDF.
        """
        # For now, return the local path
        # In production, upload to Supabase storage and return URL
        return pdf_path
    
    def generate_responses(
        self,
        user_id: str,
        job_description: str,
        company_name: str,
        job_title: str,
        additional_context: Optional[str] = None
    ) -> dict:
        """
        Generate copy-paste ready responses for job application questions.
        
        Args:
            user_id: UUID of the user from Supabase.
            job_description: Target job description.
            company_name: Name of the company.
            job_title: Title of the position.
            additional_context: Any additional context.
        
        Returns:
            Dictionary with all application responses.
        """
        self._ensure_initialized()
        start_time = time.time()
        
        print(f"📝 [Agent 4] Generating application responses...")
        print(f"   Company: {company_name}")
        print(f"   Position: {job_title}")
        
        # Fetch user profile from Supabase
        profile = self.fetch_user_profile_by_uuid(user_id)
        user_profile = self.build_resume_from_profile(profile)
        
        # Generate responses
        responses = self.generate_application_responses(
            user_profile=user_profile,
            job_description=job_description,
            company_name=company_name,
            job_title=job_title,
            additional_context=additional_context
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        print(f"   ✅ Responses generated in {processing_time}ms")
        
        return {
            "success": True,
            "user_id": user_id,
            "company_name": company_name,
            "job_title": job_title,
            "responses": responses,
            "processing_time_ms": processing_time,
            "message": "Application responses generated successfully"
        }

# Create singleton instance
agent4_service = Agent4Service()
