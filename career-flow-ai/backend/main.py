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
