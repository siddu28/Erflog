import uuid
import os
from typing import Any
from core.state import AgentState
from core.db import db_manager
# Import the new tool here
from .tools import parse_pdf, extract_structured_data, generate_embedding, upload_resume_to_storage
from pinecone import Pinecone, ServerlessSpec

def init_pinecone():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY missing in .env")
    return Pinecone(api_key=api_key)

def perception_node(state: AgentState) -> dict[str, Any]:
    try:
        pdf_path = state.get("context", {}).get("pdf_path")
        if not pdf_path:
            raise ValueError("PDF file path not provided")
        
        # 1. Generate ID EARLY (We need it for the filename)
        user_id = str(uuid.uuid4())
        print(f"[Perception] Processing New User: {user_id}")
        
        # 2. Upload Original PDF to Supabase Storage
        # This preserves the original file and links it to the User ID
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
        supabase = db_manager.get_client()
        
        profile_data = {
            "user_id": user_id,
            "name": extracted_data.get("name"),
            "email": extracted_data.get("email"),
            "skills": extracted_data.get("skills", []),
            "experience_summary": experience_summary,
            "education": extracted_data.get("education"),
            "resume_json": extracted_data,
            "resume_text": resume_text,
            "resume_url": resume_url  # ✅ Saving the S3 Link here
        }
        
        profile_response = supabase.table("profiles").insert(profile_data).execute()
        if not profile_response.data:
            raise Exception("Supabase insert failed")
            
        profile_id = profile_response.data[0]["id"]

        # 7. Store Vector -> Pinecone
        print("[Perception] Storing Vector in Pinecone (Namespace: users)...")
        pc = init_pinecone()
        index_name = os.getenv("PINECONE_INDEX_NAME", "career-agent")
        
        # Create index if missing
        if index_name not in pc.list_indexes().names():
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
        
        print(f"[Perception] Success! User Profile Created.")
        
        # 8. Update State
        updated_state = state.copy()
        updated_state["resume_text"] = resume_text
        updated_state["skills"] = extracted_data.get("skills", [])
        updated_state["user_id"] = user_id
        updated_state["summary"] = experience_summary 
        
        # Return results including the new URL
        updated_state["results"] = {
            **state.get("results", {}),
            "perception": {
                "name": extracted_data.get("name"),
                "email": extracted_data.get("email"),
                "resume_url": resume_url, # ✅ Returning URL to frontend
                "profile_id": profile_id,
                "resume_json": extracted_data
            }
        }
        
        return updated_state
    
    except Exception as e:
        print(f"[Perception] Error: {str(e)}")
        # Return error state
        updated_state = state.copy()
        updated_state["results"] = {**state.get("results", {}), "error": str(e)}
        raise e