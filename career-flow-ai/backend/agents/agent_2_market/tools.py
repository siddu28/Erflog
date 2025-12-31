"""
Agent 2: Market Sentinel - Helper Tools for Job Search and Embeddings
This module provides tools for:
1. Searching jobs using Tavily API (with hardcoded fallback)
2. Generating embeddings for job descriptions
"""

import os
from typing import Any
import google.generativeai as genai


def init_gemini():
    """Initialize Gemini API with the API key from environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set in .env")
    genai.configure(api_key=api_key)


def get_mock_jobs() -> list[dict[str, Any]]:
    """
    Return hardcoded mock job listings for fallback when Tavily fails.
    
    Returns:
        List of realistic job dictionaries
    """
    return [
        {
            "title": "Senior Python Developer",
            "company": "TechCorp Solutions",
            "link": "https://techcorp.example.com/jobs/senior-python-dev",
            "summary": "We are looking for a Senior Python Developer with 5+ years of experience in Django/FastAPI, cloud services (AWS/GCP), and database management. Experience with LLMs and AI systems is a plus."
        },
        {
            "title": "AI/ML Engineer",
            "company": "StartupX AI",
            "link": "https://startupx.example.com/careers/ai-ml-engineer",
            "summary": "Join our AI team to build cutting-edge machine learning models. Required: Python, PyTorch/TensorFlow, experience with LangChain, and familiarity with vector databases like Pinecone."
        },
        {
            "title": "Full Stack Software Engineer",
            "company": "InnovateTech Inc",
            "link": "https://innovatetech.example.com/jobs/fullstack-engineer",
            "summary": "Full Stack role requiring expertise in Python backend (FastAPI), React/Next.js frontend, PostgreSQL, and cloud deployment. Experience with REST APIs and microservices architecture preferred."
        },
    ]


def search_jobs(query: str) -> list[dict[str, Any]]:
    """
    Search for jobs using Tavily API with hardcoded fallback.
    """
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("[Market] TAVILY_API_KEY not found, using mock data")
            return get_mock_jobs()
        
        client = TavilyClient(api_key=api_key)
        
        # Search for jobs
        search_query = f"{query} job openings hiring"
        results = client.search(search_query, max_results=5)
        
        # Transform results
        jobs = []
        for result in results.get("results", []):
            content = result.get("content", "")
            job = {
                "title": result.get("title", "Job Opening"),
                "company": extract_company_from_url(result.get("url", "")),
                "link": result.get("url", ""),
                "summary": content,  # Keep for DB
            }
            jobs.append(job)
        
        if not jobs:
            return get_mock_jobs()
        
        return jobs
    
    except Exception as e:
        print(f"[Market] Error: {str(e)}")
        return get_mock_jobs()


def extract_company_from_url(url: str) -> str:
    """
    Extract a company name from a URL.
    
    Args:
        url: The URL string
        
    Returns:
        Extracted company name or "Unknown Company"
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        # Remove www. and common TLDs
        company = domain.replace("www.", "").split(".")[0]
        return company.title() if company else "Unknown Company"
    except Exception:
        return "Unknown Company"


def generate_embedding(text: str) -> list[float]:
    """
    Generate embeddings for text using Google's embedding model.
    
    Args:
        text: Text to generate embedding for (e.g., job description)
        
    Returns:
        List of floats representing the embedding vector
        
    Raises:
        Exception: If embedding generation fails
    """
    init_gemini()
    
    try:
        # Use the official embedding model
        result = genai.embed_content(
            model="models/embedding-001",
            content=text
        )
        
        # The embedding is in the 'embedding' key of the response
        embedding = result['embedding']
        
        if not isinstance(embedding, list):
            raise ValueError("Embedding is not a list")
        
        return embedding
    
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")
