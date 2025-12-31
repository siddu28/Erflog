#!/bin/bash

# DevOps Script: Setup Career Flow AI Monorepo Structure
# This script creates the complete project structure for the Agentic AI Backend

set -e

# Define root directory
ROOT_DIR="career-flow-ai"

echo "🚀 Creating Career Flow AI Monorepo Structure..."

# Create root directory
mkdir -p "$ROOT_DIR/backend"

# Create core module directories
mkdir -p "$ROOT_DIR/backend/core"

# Create agents module and all agent subdirectories
mkdir -p "$ROOT_DIR/backend/agents"
mkdir -p "$ROOT_DIR/backend/agents/agent_1_perception"
mkdir -p "$ROOT_DIR/backend/agents/agent_2_market"
mkdir -p "$ROOT_DIR/backend/agents/agent_3_strategist"
mkdir -p "$ROOT_DIR/backend/agents/agent_5_interview"

echo "✅ Directories created"

# Create __init__.py files
touch "$ROOT_DIR/backend/__init__.py"
touch "$ROOT_DIR/backend/core/__init__.py"
touch "$ROOT_DIR/backend/agents/__init__.py"
touch "$ROOT_DIR/backend/agents/agent_1_perception/__init__.py"
touch "$ROOT_DIR/backend/agents/agent_2_market/__init__.py"
touch "$ROOT_DIR/backend/agents/agent_3_strategist/__init__.py"
touch "$ROOT_DIR/backend/agents/agent_5_interview/__init__.py"

echo "✅ __init__.py files created"

# Create requirements.txt
cat > "$ROOT_DIR/backend/requirements.txt" << 'EOF'
fastapi
uvicorn
python-dotenv
langgraph
langchain
google-generativeai
supabase
pypdf
tavily-python
pydantic
EOF

echo "✅ requirements.txt created"

# Create .env.example
cat > "$ROOT_DIR/backend/.env.example" << 'EOF'
GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
TAVILY_API_KEY=your_tavily_api_key_here
EOF

echo "✅ .env.example created"

# Create README.md
cat > "$ROOT_DIR/backend/README.md" << 'EOF'
# Career Flow AI - Agentic AI Backend

A multi-agent system for career path analysis and strategizing using LangGraph and Generative AI.

## Project Structure

- **core/**: Shared logic and state management
  - `state.py`: LangGraph State definitions
  - `db.py`: Database connections (Supabase)
  
- **agents/**: Modular agent implementations
  - `agent_1_perception`: PDF and document analysis
  - `agent_2_market`: Market research and web scraping
  - `agent_3_strategist`: Strategic planning and recommendations
  - `agent_5_interview`: Voice-based interview bot

## Setup

1. Create a `.env` file from `.env.example`:
   \`\`\`bash
   cp .env.example .env
   \`\`\`

2. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

3. Set up your API keys in \`.env\`

4. Run the application:
   \`\`\`bash
   python main.py
   \`\`\`

## API Endpoints

- \`GET /\`: Health check
- \`POST /analyze\`: Submit career analysis request

## Technologies

- FastAPI: Web framework
- LangGraph: Agent orchestration
- Langchain: LLM integration
- Google Generative AI: AI models
- Supabase: Database backend
- Tavily: Web search capability
EOF

echo "✅ README.md created"

# Create core/state.py
cat > "$ROOT_DIR/backend/core/state.py" << 'EOF'
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
EOF

echo "✅ core/state.py created"

# Create core/db.py
cat > "$ROOT_DIR/backend/core/db.py" << 'EOF'
"""
Database Connection Module - Supabase Integration
"""

from os import getenv
from supabase import create_client, Client


class DatabaseManager:
    """Manages Supabase database connections."""
    
    def __init__(self):
        """Initialize database client from environment variables."""
        url = getenv("SUPABASE_URL")
        key = getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        
        self.client: Client = create_client(url, key)
    
    def get_client(self) -> Client:
        """Get the Supabase client."""
        return self.client


# Global instance
db_manager = DatabaseManager()
EOF

echo "✅ core/db.py created"

# Create main.py
cat > "$ROOT_DIR/backend/main.py" << 'EOF'
"""
Career Flow AI - Main Application Entry Point
FastAPI Server for Agentic AI Backend
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Career Flow AI Backend",
    description="Agentic AI system for career path analysis",
    version="1.0.0"
)


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "Career Flow AI Backend is running"
        }
    )


@app.post("/analyze")
async def analyze_career(request: dict):
    """
    Career analysis endpoint
    
    Request body:
    {
        "user_input": "string",
        "context": dict
    }
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Analysis request received",
            "data": {}
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
EOF

echo "✅ main.py created"

# Create agent files
cat > "$ROOT_DIR/backend/agents/agent_1_perception/graph.py" << 'EOF'
"""
Agent 1: Perception Agent - Document Analysis
Processes PDFs and extracts career-relevant information
"""


def run_perception_agent(state):
    """Execute perception agent logic"""
    return state
EOF

echo "✅ agent_1_perception/graph.py created"

cat > "$ROOT_DIR/backend/agents/agent_1_perception/tools.py" << 'EOF'
"""
Tools for Agent 1: PDF Parser and Document Extractor
"""

from pypdf import PdfReader


def extract_pdf_text(file_path: str) -> str:
    """
    Extract text from PDF file
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text content
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise ValueError(f"Error reading PDF: {e}")
EOF

echo "✅ agent_1_perception/tools.py created"

cat > "$ROOT_DIR/backend/agents/agent_2_market/graph.py" << 'EOF'
"""
Agent 2: Market Agent - Market Research and Analysis
Conducts web research and market trend analysis
"""


def run_market_agent(state):
    """Execute market agent logic"""
    return state
EOF

echo "✅ agent_2_market/graph.py created"

cat > "$ROOT_DIR/backend/agents/agent_2_market/tools.py" << 'EOF'
"""
Tools for Agent 2: Web Scraper and Search
"""

from tavily import TavilyClient


def search_market_trends(query: str) -> dict:
    """
    Search for market trends using Tavily API
    
    Args:
        query: Search query string
        
    Returns:
        Search results
    """
    client = TavilyClient()
    results = client.search(query, max_results=5)
    return results
EOF

echo "✅ agent_2_market/tools.py created"

cat > "$ROOT_DIR/backend/agents/agent_3_strategist/graph.py" << 'EOF'
"""
Agent 3: Strategist Agent - Career Path Planning
Generates strategic recommendations based on analysis
"""


def run_strategist_agent(state):
    """Execute strategist agent logic"""
    return state
EOF

echo "✅ agent_3_strategist/graph.py created"

cat > "$ROOT_DIR/backend/agents/agent_5_interview/voice_bot.py" << 'EOF'
"""
Agent 5: Interview Voice Bot
Conducts voice-based interviews and collects user information
"""


class VoiceBot:
    """Voice-based interview bot for user interaction"""
    
    def __init__(self):
        """Initialize voice bot"""
        self.conversation_history = []
    
    def start_interview(self):
        """Start an interview session"""
        return {"status": "interview_started"}
    
    def process_audio(self, audio_data: bytes) -> str:
        """
        Process audio input and return response
        
        Args:
            audio_data: Audio bytes
            
        Returns:
            Bot response
        """
        return "Processing audio..."
EOF

echo "✅ agent_5_interview/voice_bot.py created"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ ✨ Career Flow AI Monorepo Setup Complete! ✨                 ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║ 📁 Project created at: $ROOT_DIR/                             ║"
echo "║                                                                ║"
echo "║ 🚀 Next Steps:                                                 ║"
echo "║    1. cd $ROOT_DIR/backend                                    ║"
echo "║    2. cp .env.example .env                                    ║"
echo "║    3. pip install -r requirements.txt                         ║"
echo "║    4. Add your API keys to .env                               ║"
echo "║    5. python main.py                                          ║"
echo "║                                                                ║"
echo "║ 📚 Documentation: See README.md for details                   ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
