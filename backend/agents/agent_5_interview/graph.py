"""
Agent 5 - Interview (Unified Chat + Voice)
Conducts mock interviews via text or voice with LangGraph state machine.
Toggle mode: 'text' for chat, 'voice' for voice-optimized responses.
"""
import os
import json
import datetime
import time
from typing import TypedDict, List, Literal, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from core.db import db_manager

# Lazy-load LLM to ensure environment variables are loaded
_llm = None
def get_llm():
    global _llm
    if _llm is None:
        # Check for either GOOGLE_API_KEY or GEMINI_API_KEY
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables")
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0.5,  # Reduced for faster, focused responses
            google_api_key=api_key
        )
    return _llm

# Separate checkpointers for chat and voice
chat_checkpointer = MemorySaver()
voice_checkpointer = MemorySaver()

# 4-stage flow: intro -> resume -> gap_challenge -> conclusion (then end)
STAGES = {
    "intro": {"turns": 2, "next": "resume"},       # 2 turns: AI asks, user answers
    "resume": {"turns": 3, "next": "gap_challenge"},  # 3 turns: multiple Q&As
    "gap_challenge": {"turns": 4, "next": "conclusion"},  # 4 turns: challenge questions
    "conclusion": {"turns": 2, "next": "end"}       # 2 turns: ask question (0), get answer (1), then transition (2)
}
MAX_TURNS = 15  # Increased to allow full interview

class InterviewState(TypedDict):
    messages: List[BaseMessage]
    stage: str
    turn: int
    stage_turn: int
    context: dict
    feedback: Optional[dict]
    ending: bool
    mode: str  # 'text' or 'voice'

def get_stage_prompt(stage: str, ctx: dict, stage_turn: int, mode: str = "text") -> str:
    job = ctx.get('job', {})
    user = ctx.get('user', {})
    gaps = ctx.get('gaps', {})
    
    # Voice mode has extra instruction to avoid labels
    if mode == "voice":
        base = f"""You are interviewing for {job.get('title', 'Role')}. Keep responses SHORT (1-2 sentences). Ask ONE clear question. DO NOT include labels like 'Interviewer:' in your response."""
    else:
        base = f"""Interviewer for {job.get('title', 'Role')}. Keep it SHORT (1-2 sentences). ONE question."""

    if stage == "intro":
        return f"{base} Welcome and ask for a quick self-introduction."
    elif stage == "resume":
        skills = user.get('skills', [])[:2]  # Only first 2 skills
        skills_text = ', '.join(skills) if skills else 'their experience'
        return f"{base} Ask about {skills_text} or a key project."
    elif stage == "gap_challenge":
        missing = gaps.get('missing_skills', [])[:1]  # Only first missing skill
        skill = missing[0] if missing else 'problem-solving'
        return f"{base} Ask about their experience or approach to {skill}."
    elif stage == "conclusion":
        # Single conclusion message - thank and close
        return f"{base} CRITICAL: Max 15 words. Say: 'Thanks for your time today. We'll review and be in touch soon. Goodbye!'"
    
    return base

def interviewer_node(state: InterviewState) -> dict:
    mode = state.get("mode", "text")
    stage = state.get("stage", "intro")
    turn = state.get("turn", 0)
    stage_turn = state.get("stage_turn", 0)
    ctx = state.get("context", {})
    messages = state.get("messages", [])
    
    log_prefix = "[Voice Interviewer]" if mode == "voice" else "[Chat Interviewer]"
    print(f"{log_prefix} Stage: {stage}, Turn: {turn}, StageTurn: {stage_turn}, Ending: {state.get('ending', False)}")
    
    # Voice mode: Special handling for conclusion - after user answers (stage_turn=1), end immediately
    if mode == "voice" and stage == "conclusion" and stage_turn >= 1:
        print(f"{log_prefix} Conclusion answer received, ending interview")
        return {
            "messages": messages,
            "stage": "end",
            "turn": turn,
            "stage_turn": stage_turn,
            "ending": True
        }
    
    # Check if we need to transition BEFORE generating next question
    stage_order = ["intro", "resume", "gap_challenge", "conclusion", "end"]
    current_idx = stage_order.index(stage) if stage in stage_order else 0
    config = STAGES.get(stage, {"turns": 2, "next": "end"})
    
    if stage_turn >= config["turns"]:
        next_stage = config["next"]
        next_idx = stage_order.index(next_stage) if next_stage in stage_order else len(stage_order) - 1
        
        if next_idx > current_idx:
            print(f"{log_prefix} ✅ TRANSITIONING: {stage} -> {next_stage} (StageTurn {stage_turn}/{config['turns']})")
            
            # Voice mode: If transitioning to end, just mark as ending without generating message
            if mode == "voice" and next_stage == "end":
                print(f"{log_prefix} Ending interview - no more messages")
                return {
                    "messages": messages,
                    "stage": "end",
                    "turn": turn,
                    "stage_turn": stage_turn,
                    "ending": True
                }
            
            stage = next_stage
            stage_turn = 0
            if next_stage == "end":
                state = {**state, "ending": True}
    
    if stage == "end" or state.get("ending", False) or turn >= MAX_TURNS:
        print(f"{log_prefix} Triggering conclusion - Stage:{stage}, Ending:{state.get('ending')}, Turn:{turn}/{MAX_TURNS}")
        
        # Voice mode: Return early without generating more messages
        if mode == "voice":
            return {
                "messages": messages,
                "stage": "end",
                "ending": True
            }
        
        # Text mode: Generate final conclusion message
        prompt = get_stage_prompt("conclusion", ctx, 1, mode) + " Final message."
        response = get_llm().invoke(messages[-4:] + [HumanMessage(content=prompt)])
        return {
            "messages": messages + [AIMessage(content=response.content)],
            "stage": "end",
            "ending": True
        }
    
    prompt = get_stage_prompt(stage, ctx, stage_turn, mode)
    
    # Voice mode: Add timing metrics
    if mode == "voice":
        start_time = time.time()
        response = get_llm().invoke(messages[-4:] + [HumanMessage(content=prompt)])
        elapsed = time.time() - start_time
        print(f"{log_prefix} LLM took {elapsed:.2f}s")
    else:
        response = get_llm().invoke(messages[-4:] + [HumanMessage(content=prompt)])
    
    ai_content = response.content
    
    # Voice mode: Strip unwanted prefixes and truncate long responses
    if mode == "voice":
        ai_content = ai_content.replace("Interviewer:", "").replace("Interviewer :", "").strip()
        
        # Truncate conclusion responses if too long (prevent 30s TTS times)
        if stage == "conclusion" and len(ai_content) > 150:
            print(f"{log_prefix} ⚠️ Truncating long conclusion: {len(ai_content)} chars -> 150")
            ai_content = ai_content[:150] + "..."
        
        # Strip markdown formatting for TTS
        ai_content = ai_content.replace('**', '').replace('*', '').replace('_', '')
    
    new_state = {
        "messages": messages + [AIMessage(content=ai_content)],
        "stage": stage,
        "turn": turn + 1,
        "stage_turn": stage_turn + 1
    }
    
    print(f"{log_prefix} Output - Stage: {new_state.get('stage', stage)}, Turn: {new_state['turn']}, StageTurn: {new_state['stage_turn']}")
    return new_state

def check_stage_transition(state: InterviewState) -> dict:
    mode = state.get("mode", "text")
    stage = state.get("stage", "intro")
    stage_turn = state.get("stage_turn", 0)
    turn = state.get("turn", 0)
    
    log_prefix = "[Voice Transition]" if mode == "voice" else "[Transition]"
    
    # Define stage order to prevent backwards movement
    stage_order = ["intro", "resume", "gap_challenge", "conclusion", "end"]
    current_idx = stage_order.index(stage) if stage in stage_order else 0
    
    config = STAGES.get(stage, {"turns": 2, "next": "end"})
    print(f"{log_prefix} Stage: {stage}, StageTurn: {stage_turn}/{config['turns']}")
    
    # Only advance if we've completed enough turns in this stage
    if stage_turn >= config["turns"]:
        next_stage = config["next"]
        next_idx = stage_order.index(next_stage) if next_stage in stage_order else len(stage_order) - 1
        
        # CRITICAL: Only move forward, never backwards
        if next_idx > current_idx:
            updates = {"stage": next_stage, "stage_turn": 0}
            if next_stage == "end":
                updates["ending"] = True
            print(f"{log_prefix} ✅ Advancing: {stage} -> {next_stage} (Turn {turn})")
            return updates
        else:
            print(f"{log_prefix} ❌ BLOCKED backwards movement from {stage} to {next_stage}")
    else:
        print(f"{log_prefix} STAYING in {stage} - need {config['turns']} turns, at {stage_turn}")
    
    return {}

def should_continue(state: InterviewState) -> Literal["continue", "evaluate"]:
    mode = state.get("mode", "text")
    stage = state.get("stage")
    ending = state.get("ending", False)
    
    log_prefix = "[Voice should_continue]" if mode == "voice" else "[ShouldContinue]"
    
    if stage == "end" or ending:
        print(f"{log_prefix} → Routing to EVALUATE")
        return "evaluate"
    print(f"{log_prefix} → Routing to CONTINUE")
    return "continue"

def evaluate_node(state: InterviewState) -> dict:
    mode = state.get("mode", "text")
    log_prefix = "[Voice Evaluate]" if mode == "voice" else "[Evaluate]"
    print(f"{log_prefix} Starting evaluation...")
    
    ctx = state.get("context", {})
    messages = state.get("messages", [])
    
    job_title = ctx.get('job', {}).get('title', 'this position')
    
    prompt = f"""Evaluate interview for {job_title}. Return JSON:
{{
    "score": <0-100>,
    "verdict": "Hired" or "Not Hired",
    "summary": "<brief 2-line evaluation>",
    "strengths": ["s1", "s2"],
    "improvements": ["i1", "i2"]
}}"""
    
    response = get_llm().invoke(messages[-8:] + [HumanMessage(content=prompt)])
    try:
        feedback = json.loads(response.content.replace("```json", "").replace("```", "").strip())
    except:
        feedback = {"score": 0, "verdict": "Error"}
    
    # Save to DB
    try:
        user_id = ctx.get("user_id")
        job_id = ctx.get("job_id")
        if user_id:
            chat_history = [{"role": m.type, "content": m.content} for m in messages]
            
            # Convert job_id to int, handle float strings like "113.0"
            job_id_int = None
            if job_id:
                try:
                    job_id_int = int(float(job_id))
                except (ValueError, TypeError):
                    print(f"⚠️ [DB] Invalid job_id: {job_id}, saving without job reference")
            
            # Build insert data
            insert_data = {
                "user_id": user_id,
                "chat_history": json.dumps(chat_history),
                "feedback_report": json.dumps(feedback),
                "created_at": datetime.datetime.now().isoformat()
            }
            
            # Only add job_id if it's valid (to avoid foreign key constraint)
            if job_id_int is not None:
                insert_data["job_id"] = job_id_int
            
            try:
                db_manager.get_client().table("interviews").insert(insert_data).execute()
                print(f"✅ [DB] Saved interview feedback for User {user_id}" + (f" Job {job_id_int}" if job_id_int else " (no job reference)"))
            except Exception as db_error:
                # If job_id causes foreign key error, retry without it
                if "23503" in str(db_error) and job_id_int is not None:
                    print(f"⚠️ [DB] Job {job_id_int} not in database, saving without job reference")
                    insert_data.pop("job_id", None)
                    db_manager.get_client().table("interviews").insert(insert_data).execute()
                    print(f"✅ [DB] Saved interview feedback for User {user_id} (no job reference)")
                else:
                    raise
    except Exception as e:
        print(f"❌ [DB] Save Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"{log_prefix} Complete - Verdict: {feedback.get('verdict', 'N/A')}, Score: {feedback.get('score', 0)}")
    return {"feedback": feedback, "stage": "end"}

# Build workflow graphs for both modes
def _build_graph(checkpointer):
    workflow = StateGraph(InterviewState)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("evaluate", evaluate_node)
    
    workflow.add_edge(START, "interviewer")
    workflow.add_conditional_edges("interviewer", should_continue, {"continue": "interviewer", "evaluate": "evaluate"})
    workflow.add_edge("evaluate", END)
    
    return workflow.compile(checkpointer=checkpointer, interrupt_after=["interviewer"])

# Create both interview graphs
chat_interview_graph = _build_graph(chat_checkpointer)
voice_interview_graph = _build_graph(voice_checkpointer)

def create_initial_state(context: dict, mode: str = "text") -> InterviewState:
    """Create initial interview state with mode toggle."""
    return {
        "messages": [],
        "stage": "intro",
        "turn": 0,
        "stage_turn": 0,
        "context": context,
        "feedback": None,
        "ending": False,
        "mode": mode
    }

# Convenience aliases for backwards compatibility
def create_chat_state(context: dict) -> InterviewState:
    return create_initial_state(context, mode="text")

def create_voice_state(context: dict) -> InterviewState:
    return create_initial_state(context, mode="voice")

def add_user_message(state: dict, user_text: str) -> dict:
    return {
        **state,
        "messages": state.get("messages", []) + [HumanMessage(content=user_text)]
    }

# Convenience aliases for backwards compatibility
add_chat_message = add_user_message
add_voice_message = add_user_message

def run_interview_turn(session_id: str, user_message: str, job_context: str) -> dict:
    """
    Run a single interview turn. Returns the AI response and current state.
    """
    # Create a simple context from job_context string
    context = {
        "job": {"title": job_context, "company": "Company"},
        "user": {"name": "Candidate", "skills": []},
        "gaps": {"missing_skills": [], "suggested_questions": []},
        "user_id": session_id,
        "job_id": "1"
    }
    
    thread_id = f"interview_{session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get or create initial state
    try:
        # Try to get existing state from checkpointer
        state = create_chat_state(context)
        if user_message:
            state = add_user_message(state, user_message)
        
        result = chat_interview_graph.invoke(state, config=config)
        
        ai_response = result["messages"][-1].content if result["messages"] else "Hello!"
        
        return {
            "response": ai_response,
            "stage": result.get("stage", "intro"),
            "message_count": len(result.get("messages", []))
        }
    except Exception as e:
        print(f"Interview error: {e}")
        return {
            "response": "I apologize, there was an error. Could you repeat that?",
            "stage": "intro",
            "message_count": 0
        }
