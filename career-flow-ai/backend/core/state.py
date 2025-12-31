"""
LangGraph State Definition for Agent State Management
"""

from typing import TypedDict, Any


class AgentState(TypedDict):
    """
    Central state object passed between agents in the LangGraph workflow.
    
    Attributes:
        user_input: Initial user query or request
        context: Additional context for processing
        results: Accumulated results from various agents
        messages: Conversation history
        metadata: Additional metadata for tracking
    """
    user_input: str
    context: dict[str, Any]
    results: dict[str, Any]
    messages: list[dict[str, str]]
    metadata: dict[str, Any]
