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
