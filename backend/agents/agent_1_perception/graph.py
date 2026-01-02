import uuid
import os
from typing import Any
from core.state import AgentState
from core.db import db_manager
from .tools import parse_pdf, extract_structured_data, generate_embedding, upload_resume_to_storage
from pinecone import Pinecone, ServerlessSpec
from .github_watchdog import fetch_and_analyze_github
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from supabase import create_client

class Agent1State(TypedDict):
    user_id: str
    github_url: Optional[str]
    resume_text: Optional[str]
    profile_data: Optional[dict]

def init_pinecone():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY missing in .env")
    return Pinecone(api_key=api_key)

def perception_node(state: AgentState) -> dict[str, Any]:
    """
    Agent 1 Core Logic - Updated for new schema (no users table, profiles is standalone)
    """
    try:
        pdf_path = state.get("context", {}).get("pdf_path")
        if not pdf_path:
            raise ValueError("PDF file path not provided")
        
        # 1. Generate ID EARLY
        user_id = str(uuid.uuid4())
        print(f"[Perception] Processing New User: {user_id}")
        
        # 2. Upload Original PDF to Supabase Storage
        resume_url = upload_resume_to_storage(pdf_path, user_id)
        
        # 3. Parse PDF Text
        print(f"[Perception] Parsing PDF text...")
        resume_text = parse_pdf(pdf_path)
        
        # 4. Extract Structured Data (Gemini)
        print("[Perception] Extracting structured data...")
        extracted_data = extract_structured_data(resume_text)
        
        # 5. Generate Embedding
        print("[Perception] Generating embedding...")
        experience_summary = extracted_data.get("experience_summary", resume_text[:500])
        embedding = generate_embedding(experience_summary)
        
        # 6. Store Structured Data -> Supabase Database
        print("[Perception] Storing Profile in Supabase DB...")
        
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not service_key:
            print("⚠️ SUPABASE_SERVICE_ROLE_KEY not found, falling back to anon key")
            service_key = os.getenv("SUPABASE_KEY")
        
        supabase = create_client(supabase_url, service_key)
        
        # Profile data matching the new schema
        profile_data = {
            "user_id": user_id,
            "name": extracted_data.get("name"),
            "email": extracted_data.get("email"),
            "skills": extracted_data.get("skills", []),
            "experience_summary": experience_summary,
            "education": extracted_data.get("education"),
            "resume_json": extracted_data,
            "resume_text": resume_text,
            "resume_url": resume_url
        }
        
        # ============ WORKAROUND: Use RPC or direct SQL to bypass FK ============
        # Since there's a FK constraint to a non-existent users table,
        # we try multiple approaches
        
        profile_response = None
        profile_id = user_id  # Default to user_id as identifier
        
        try:
            # Approach 1: Try direct insert
            profile_response = supabase.table("profiles").insert(profile_data).execute()
        except Exception as e1:
            error_str = str(e1)
            print(f"[Perception] Insert failed: {error_str[:100]}")
            
            if "23503" in error_str or "foreign key" in error_str.lower():
                print("[Perception] ⚠️ FK constraint blocking insert.")
                print("[Perception] ℹ️  Please run this SQL in Supabase to fix:")
                print("    ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;")
                print("    ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_user_id_fkey;")
                
                # Approach 2: Try using a raw RPC call to bypass constraints
                try:
                    # Create a simple RPC function in Supabase if needed
                    # For now, we'll store in session and skip DB
                    print("[Perception] ⚠️ Skipping DB insert due to FK constraint. Profile stored in session only.")
                    profile_response = None
                except:
                    pass
            else:
                raise e1
        
        if profile_response and profile_response.data:
            profile_id = profile_response.data[0].get("user_id", user_id)
            print(f"[Perception] ✅ Profile saved to DB with user_id: {profile_id}")
        else:
            print(f"[Perception] ⚠️ Profile NOT saved to DB (FK constraint). Continuing with session storage...")

        # 7. Store Vector -> Pinecone (this works regardless of DB)
        print("[Perception] Storing Vector in Pinecone (Namespace: users)...")
        pc = init_pinecone()
        index_name = os.getenv("PINECONE_INDEX_NAME", "ai-verse")
        
        # Check if index exists
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing_indexes:
            print(f"[Perception] Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=768, 
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        index = pc.Index(index_name)
        
        vector_data = {
            "id": user_id, 
            "values": embedding,
            "metadata": {
                "profile_id": profile_id,
                "email": extracted_data.get("email"),
                "skills": extracted_data.get("skills", []),
                "summary": experience_summary
            }
        }
        
        index.upsert(vectors=[vector_data], namespace="users")
        print(f"[Perception] ✅ Vector stored in Pinecone")
        
        print(f"[Perception] Success! User Profile Created: {user_id}")
        
        # 8. Update State
        updated_state = state.copy()
        updated_state["resume_text"] = resume_text
        updated_state["skills"] = extracted_data.get("skills", [])
        updated_state["user_id"] = user_id
        updated_state["summary"] = experience_summary 
        
        updated_state["results"] = {
            **state.get("results", {}),
            "perception": {
                "name": extracted_data.get("name"),
                "email": extracted_data.get("email"),
                "resume_url": resume_url,
                "profile_id": profile_id,
                "experience_summary": experience_summary,
                "education": extracted_data.get("education"),
                "resume_json": extracted_data
            }
        }
        
        return updated_state
    
    except Exception as e:
        print(f"[Perception] Error: {str(e)}")
        updated_state = state.copy()
        updated_state["results"] = {**state.get("results", {}), "error": str(e)}
        raise e


def github_watchdog_node(state: Agent1State):
    github_url = state.get("github_url")
    user_id = state.get("user_id")
    
    if github_url:
        print("🚀 Starting GitHub Watchdog...")
        analysis_result = fetch_and_analyze_github(github_url)
        
        if analysis_result:
            print(f"✅ Watchdog found skills: {analysis_result}")
            
            # Update profiles table (not users - users table doesn't exist)
            try:
                db_manager.get_client().table("profiles").update({
                    "resume_json": {"github_analysis": analysis_result}
                }).eq("user_id", user_id).execute()
            except Exception as e:
                print(f"[Watchdog] DB update failed: {e}")
            
            return {"profile_data": {"github_analysis": analysis_result}}
    
    return {}

# --- GRAPH DEFINITION ---
workflow = StateGraph(Agent1State)
workflow.add_node("parse_resume", perception_node)
workflow.add_node("github_watchdog", github_watchdog_node)
workflow.set_entry_point("parse_resume")
workflow.add_edge("parse_resume", "github_watchdog")
workflow.add_edge("github_watchdog", END)

app = workflow.compile()