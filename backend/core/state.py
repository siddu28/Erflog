"""
LangGraph State Definition for Agent State Management
"""

from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    """
    Central state object passed between agents in the LangGraph workflow.
    
    Attributes:
        resume_text: Raw text extracted from the resume PDF
        skills: List of extracted skills from the resume
        user_id: Unique identifier for the user profile
        context: Dictionary to store file paths and additional context
        results: Dictionary to store results and logs from agents
    """
    resume_text: Optional[str]
    skills: list[str]
    user_id: Optional[str]
    context: dict
    results: dict
