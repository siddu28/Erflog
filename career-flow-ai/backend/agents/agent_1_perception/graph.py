# ... (Imports remain the same) ...
import uuid
from typing import Any
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

# Keep your existing project imports
from core.state import AgentState
from core.db import db_manager
from .tools import parse_pdf, extract_structured_data, generate_embedding

load_dotenv()


def init_pinecone():
    """Initialize Pinecone client safely."""
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("CRITICAL: PINECONE_API_KEY is missing in .env")
    return Pinecone(api_key=api_key)


def perception_node(state: AgentState) -> dict[str, Any]:
    try:
        # ... (PDF Parsing and Gemini Extraction Logic stays the same) ...
        # [Copy steps 1-5 from your previous code here, or just paste the whole function below]
        
        pdf_path = state.get("context", {}).get("pdf_path")
        if not pdf_path:
            raise ValueError("PDF file path not provided")
        
        print(f"👁️ [Perception] Processing: {pdf_path}")

        # --- Step 1: Parse PDF ---
        resume_text = parse_pdf(pdf_path)
        
        # 2. Extract Data
        print("[Perception] Extracting structured data...")
        extracted_data = extract_structured_data(resume_text)
        
        # 3. Generate Embedding
        print("[Perception] Generating embedding...")
        experience_summary = extracted_data.get("experience_summary", resume_text[:500])
        embedding = generate_embedding(experience_summary)
        
        # 4. Generate IDs
        user_id = str(uuid.uuid4())
        
        # --- Step 5: Store in Supabase (SQL) ---
        print("💾 [Perception] Storing profile in Supabase...")
        supabase = db_manager.get_client()
        
        profile_payload = {
            "user_id": user_id,
            "name": extracted_data.get("name", "Unknown Candidate"),
            "email": extracted_data.get("email"),
            "skills": extracted_data.get("skills", []),
            "experience_summary": extracted_data.get("experience_summary"),
            "education": extracted_data.get("education", []),
            "resume_json": extracted_data,
        }
        
        profile_response = supabase.table("profiles").insert(profile_data).execute()
        if not profile_response.data:
            raise Exception("Supabase insert failed")
            
        # This ID links the SQL row to the Vector
        profile_db_id = response.data[0]["id"] 

        # 6. Store Vector -> Pinecone (NAMESPACE ADDED HERE)
        print("[Perception] Storing Vector in Pinecone (Namespace: users)...")
        pc = init_pinecone()
        index_name = os.getenv("PINECONE_INDEX_NAME", "career-agent")
        
        if index_name not in pc.list_indexes().names():
            print(f"Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=768, 
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

        index = pc.Index(index_name)
        
        vector_data = {
            "id": user_id, 
            "values": embedding,
            "metadata": {
                "profile_id": profile_db_id,  # Foreign Key to Supabase
                "email": extracted_data.get("email"),
                "skills": extracted_data.get("skills", []),
                "type": "candidate"
            }
        }
        
        # --- THE CHANGE IS HERE ---
        index.upsert(vectors=[vector_data], namespace="users")
        # --------------------------
        
        print(f"[Perception] Success! User: {user_id}")
        
        # 7. Update State
        updated_state = state.copy()
        updated_state["resume_text"] = resume_text
        updated_state["skills"] = extracted_data.get("skills", [])
        updated_state["user_id"] = user_id
        
        return updated_state
    
    except Exception as e:
        print(f"❌ [Perception] Error: {str(e)}")
        raise e


# Build the graph
def build_graph() -> StateGraph:
    """
    Builds and returns the Agent 1 Perception workflow graph.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("perception", perception_node)
    
    # Define the flow: START -> perception -> END
    workflow.add_edge(START, "perception")
    workflow.add_edge("perception", END)
    
    return workflow


# Compile the graph
workflow = build_graph()
app = workflow.compile()


def run_agent1(pdf_path: str) -> dict[str, Any]:
    """
    Convenience function to run the Agent 1 workflow.
    
    Args:
        pdf_path: Path to the resume PDF file.
    
    Returns:
        The final state after workflow execution.
    """
    initial_state: AgentState = {
        "pdf_path": pdf_path,
        "context": {"pdf_path": pdf_path},
        "user_id": "",
        "profile_data": {},
        "resume_text": "",
        "status": "pending"
    }
    
    result = app.invoke(initial_state)
    return result