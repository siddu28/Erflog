# backend/agents/agent_1_perception/service.py
import os
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, HTTPException
from supabase import create_client
from pinecone import Pinecone

# Import tools
from .tools import (
    parse_pdf, 
    extract_structured_data, 
    generate_embedding, 
    upload_resume_to_storage,
    generate_skill_quiz
)
from .github_watchdog import (
    fetch_user_recent_activity,
    analyze_code_context,
    extract_username_from_url,
    get_latest_commit_sha
)


class PerceptionService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Init Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow")
        self.index = self.pc.Index(self.index_name)

    # =========================================================================
    # RESUME PROCESSING
    # =========================================================================
    
    async def process_resume_upload(self, file: UploadFile, user_id: str) -> dict:
        """
        Handles the full flow: PDF Save -> Parse -> Gemini -> DB -> Pinecone
        Now also initializes skills_metadata for resume-extracted skills.
        """
        # 1. Save File Temporarily
        temp_dir = Path(tempfile.gettempdir()) / "agent1_uploads"
        temp_dir.mkdir(exist_ok=True)
        pdf_path = temp_dir / f"{user_id}_{file.filename}"
        
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # 2. Upload to Storage (Long-term)
            resume_url = upload_resume_to_storage(str(pdf_path), user_id)

            # 3. Parse & Extract
            resume_text = parse_pdf(str(pdf_path))
            extracted_data = extract_structured_data(resume_text)
            
            # 4. Generate Vector
            summary = extracted_data.get("experience_summary", resume_text[:500])
            embedding = generate_embedding(summary)

            # 5. Build skills_metadata from extracted skills
            skills_list = extracted_data.get("skills", [])
            now = datetime.utcnow().isoformat()
            
            skills_metadata = {}
            for skill in skills_list:
                skills_metadata[skill] = {
                    "source": "resume",
                    "verification_status": "pending",
                    "level": None,
                    "evidence": "Listed in resume",
                    "last_seen": now
                }

            # 6. Prepare DB Record (Supabase Profiles)
            profile_data = {
                "user_id": user_id,
                "name": extracted_data.get("name"),
                "email": extracted_data.get("email"),
                "skills": skills_list,  # Legacy array
                "skills_metadata": skills_metadata,  # Rich metadata
                "experience_summary": summary,
                "education": extracted_data.get("education"),
                "resume_json": extracted_data,
                "resume_text": resume_text,
                "resume_url": resume_url,
            }

            # 7. Upsert to DB
            self.supabase.table("profiles").upsert(profile_data).execute()

            # 8. Upsert to Pinecone
            vector_data = {
                "id": user_id, 
                "values": embedding,
                "metadata": {
                    "email": extracted_data.get("email") or "",
                    "skills": skills_list,
                    "type": "user_profile"
                }
            }
            self.index.upsert(vectors=[vector_data], namespace="users")

            return profile_data

        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    # =========================================================================
    # ONBOARDING
    # =========================================================================
    
    async def update_user_onboarding(
        self,
        user_id: str,
        github_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        target_roles: Optional[List[str]] = None
    ) -> dict:
        """Updates user profile with onboarding information."""
        update_data = {}
        updated_fields = []
        
        if github_url is not None:
            username = extract_username_from_url(github_url)
            if not username:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid GitHub URL format. Expected: https://github.com/username"
                )
            update_data["github_url"] = github_url
            updated_fields.append("github_url")
            
        if linkedin_url is not None:
            update_data["linkedin_url"] = linkedin_url
            updated_fields.append("linkedin_url")
            
        if target_roles is not None:
            update_data["target_roles"] = target_roles
            updated_fields.append("target_roles")
        
        if not update_data:
            return {"status": "no_changes", "updated_fields": [], "user_id": user_id}
        
        self.supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        
        return {"status": "success", "updated_fields": updated_fields, "user_id": user_id}

    # =========================================================================
    # GITHUB WATCHDOG (Refactored for skills_metadata)
    # =========================================================================
    
    async def run_github_watchdog(self, user_id: str) -> Optional[dict]:
        """
        Scans user's GitHub activity stream for skill analysis.
        
        REFACTORED: Now updates skills_metadata instead of just appending to skills array.
        - New skills: source="github", verification_status="pending"
        - Existing skills: Updates evidence and last_seen
        - Syncs skills_metadata keys to legacy skills array
        """
        # 1. Get user's profile from database
        response = self.supabase.table("profiles").select(
            "github_url, skills, skills_metadata"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found. Please upload your resume first.")
        
        profile = response.data[0]
        github_url = profile.get("github_url")
        current_skills = profile.get("skills") or []
        current_metadata = profile.get("skills_metadata") or {}
        
        if not github_url:
            raise HTTPException(
                status_code=400,
                detail="GitHub URL not set. Please complete onboarding first via PATCH /api/perception/onboarding"
            )
        
        # 2. Extract username from URL
        username = extract_username_from_url(github_url)
        if not username:
            raise HTTPException(status_code=400, detail=f"Invalid GitHub URL format: {github_url}")
        
        print(f"[Watchdog] Scanning GitHub activity for user: {username}")
        
        # 3. Fetch recent activity from Events API
        activity = fetch_user_recent_activity(username)
        
        if not activity or not activity.get("recent_code_context"):
            print(f"[Watchdog] No recent code activity found for {username}")
            return {
                "updated_skills": current_skills,
                "skills_metadata": current_metadata,
                "analysis": None,
                "message": "No recent code activity found on GitHub"
            }
        
        # 4. Analyze the code context
        analysis = analyze_code_context(activity["recent_code_context"])
        
        if not analysis:
            return {
                "updated_skills": current_skills,
                "skills_metadata": current_metadata,
                "analysis": None,
                "message": "Could not analyze code context"
            }
        
        # 5. Update skills_metadata with detected skills
        now = datetime.utcnow().isoformat()
        detected_skills = analysis.get('detected_skills', [])
        
        for item in detected_skills:
            skill_name = item.get('skill')
            level = item.get('level', 'intermediate')
            evidence = item.get('evidence', 'Detected in recent GitHub activity')
            
            if skill_name in current_metadata:
                # Skill exists - update evidence and last_seen
                # Don't downgrade verification_status if already verified
                current_metadata[skill_name]["evidence"] = evidence
                current_metadata[skill_name]["last_seen"] = now
                if current_metadata[skill_name].get("level") is None:
                    current_metadata[skill_name]["level"] = level
            else:
                # New skill from GitHub
                current_metadata[skill_name] = {
                    "source": "github",
                    "verification_status": "pending",
                    "level": level,
                    "evidence": evidence,
                    "last_seen": now
                }
        
        # 6. Sync skills array from skills_metadata keys (for backward compatibility)
        final_skills = list(current_metadata.keys())
        
        # 7. Update Database with both columns
        self.supabase.table("profiles").update({
            "skills": final_skills,
            "skills_metadata": current_metadata,
            "last_scan_timestamp": "now()"
        }).eq("user_id", user_id).execute()
        
        # 8. Update Pinecone metadata
        try:
            self.index.update(
                id=user_id,
                set_metadata={"skills": final_skills},
                namespace="users"
            )
        except Exception as e:
            print(f"[Watchdog] Pinecone update warning: {e}")
        
        return {
            "updated_skills": final_skills,
            "skills_metadata": current_metadata,
            "analysis": analysis,
            "repos_touched": activity.get("repos_touched", []),
            "latest_sha": activity.get("latest_commit_sha")
        }

    # =========================================================================
    # GITHUB ACTIVITY CHECK (Polling)
    # =========================================================================
    
    async def check_github_activity(
        self, 
        user_id: str, 
        last_known_sha: Optional[str] = None
    ) -> dict:
        """Quick check for new GitHub activity (used for polling)."""
        response = self.supabase.table("profiles").select("github_url").eq("user_id", user_id).execute()
        
        if not response.data or not response.data[0].get("github_url"):
            return {"status": "no_github", "message": "GitHub URL not configured"}
        
        github_url = response.data[0]["github_url"]
        username = extract_username_from_url(github_url)
        
        if not username:
            return {"status": "error", "message": "Invalid GitHub URL"}
        
        current_sha = get_latest_commit_sha(username)
        
        if not current_sha:
            return {"status": "no_activity", "message": "No recent activity found"}
        
        if last_known_sha == current_sha:
            return {"status": "no_change", "current_sha": current_sha}
        
        print(f"🔔 New GitHub activity detected for {username} (SHA: {current_sha[:7]})")
        
        result = await self.run_github_watchdog(user_id)
        
        return {
            "status": "updated",
            "new_sha": current_sha,
            "updated_skills": result.get("updated_skills", []) if result else [],
            "skills_metadata": result.get("skills_metadata", {}) if result else {},
            "analysis": result.get("analysis") if result else None,
            "repos_touched": result.get("repos_touched", []) if result else []
        }

    # =========================================================================
    # SKILL VERIFICATION: Quiz
    # =========================================================================
    
    async def generate_quiz(
        self, 
        user_id: str, 
        skill_name: str, 
        level: str = "intermediate"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a quiz question for skill verification.
        
        Args:
            user_id: Authenticated user's ID
            skill_name: Skill to verify (e.g., "React")
            level: Difficulty level
            
        Returns:
            Dict with quiz_id, question, options, and correct_index
        """
        # Verify user has this skill in their profile
        response = self.supabase.table("profiles").select("skills_metadata").eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        skills_metadata = response.data[0].get("skills_metadata") or {}
        
        # Allow quiz even if skill not in profile (for adding new skills)
        if skill_name in skills_metadata:
            # Use existing level if available
            existing_level = skills_metadata[skill_name].get("level")
            if existing_level:
                level = existing_level
        
        # Generate quiz using LangChain tool
        quiz_data = generate_skill_quiz(skill_name, level)
        
        if not quiz_data:
            raise HTTPException(status_code=500, detail="Failed to generate quiz question")
        
        # Create unique quiz ID
        quiz_id = str(uuid.uuid4())
        
        return {
            "quiz_id": quiz_id,
            "skill_name": skill_name,
            "question": quiz_data["question"],
            "options": quiz_data["options"],
            "correct_index": quiz_data["correct_index"],  # In production, store server-side
            "explanation": quiz_data.get("explanation", "")
        }

    async def verify_quiz_attempt(
        self,
        user_id: str,
        skill_name: str,
        passed: bool
    ) -> Dict[str, Any]:
        """
        Update skill verification status based on quiz result.
        
        Args:
            user_id: Authenticated user's ID
            skill_name: Skill that was tested
            passed: Whether the user answered correctly
            
        Returns:
            Dict with new_status and message
        """
        # Get current profile
        response = self.supabase.table("profiles").select(
            "skills, skills_metadata"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = response.data[0]
        skills_metadata = profile.get("skills_metadata") or {}
        skills_list = profile.get("skills") or []
        
        now = datetime.utcnow().isoformat()
        
        if passed:
            # Update or create skill metadata with verified status
            if skill_name in skills_metadata:
                skills_metadata[skill_name]["verification_status"] = "verified"
                skills_metadata[skill_name]["last_seen"] = now
            else:
                # Add new skill via quiz verification
                skills_metadata[skill_name] = {
                    "source": "quiz",
                    "verification_status": "verified",
                    "level": "intermediate",
                    "evidence": "Passed verification quiz",
                    "last_seen": now
                }
            
            # Sync skills array
            if skill_name not in skills_list:
                skills_list.append(skill_name)
            
            new_status = "verified"
            message = f"🎉 Congratulations! Your {skill_name} skill has been verified."
        else:
            # Don't change status on failure, but log the attempt
            if skill_name in skills_metadata:
                skills_metadata[skill_name]["last_seen"] = now
            
            new_status = skills_metadata.get(skill_name, {}).get("verification_status", "pending")
            message = f"Not quite right. Your {skill_name} status remains: {new_status}"
        
        # Update database
        self.supabase.table("profiles").update({
            "skills": skills_list,
            "skills_metadata": skills_metadata
        }).eq("user_id", user_id).execute()
        
        # Update Pinecone if skills changed
        try:
            self.index.update(
                id=user_id,
                set_metadata={"skills": skills_list},
                namespace="users"
            )
        except Exception as e:
            print(f"[Quiz] Pinecone update warning: {e}")
        
        return {
            "correct": passed,
            "new_status": new_status,
            "message": message,
            "skills_metadata": skills_metadata.get(skill_name, {})
        }


# Singleton Instance
agent1_service = PerceptionService()
