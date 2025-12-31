"""
Agent 1 Perception - Helper Tools for PDF Processing and Data Extraction
This module provides tools for:
1. Parsing PDF files
2. Extracting structured data using Gemini 1.5 Flash
3. Generating embeddings for similarity search
"""

import json
import os
from typing import Any
import google.generativeai as genai
from pypdf import PdfReader


def init_gemini():
    """Initialize Gemini API with the API key from environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set in .env")
    genai.configure(api_key=api_key)


def parse_pdf(file_path: str) -> str:
    """
    Parse a PDF file and extract all text.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text from the PDF
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If PDF parsing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")


def extract_structured_data(text: str) -> dict[str, Any]:
    """
    Extract structured data from resume text using Gemini 1.5 Flash.
    
    Args:
        text: Raw text from the resume/PDF
        
    Returns:
        Dictionary with keys: name, email, skills (list), experience_summary, education
        
    Raises:
        Exception: If Gemini API call fails or response is invalid
    """
    init_gemini()
    
    prompt = f"""
    Please analyze the following resume/document text and extract the following information in JSON format:
    
    {{
        "name": "Full name of the person",
        "email": "Email address",
        "skills": ["skill1", "skill2", "skill3", ...],
        "experience_summary": "Brief summary of professional experience",
        "education": "Education details (degrees, universities, etc.)"
    }}
    
    Resume Text:
    {text}
    
    Return ONLY valid JSON, no other text.
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to parse JSON from the response
        # If response contains markdown code blocks, extract the JSON
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text
        
        data = json.loads(json_str)
        
        # Validate required fields
        required_fields = ["name", "email", "skills", "experience_summary", "education"]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        # Ensure skills is a list
        if not isinstance(data.get("skills"), list):
            data["skills"] = [str(data.get("skills", ""))] if data.get("skills") else []
        
        return data
    
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON from Gemini response: {str(e)}")
    except Exception as e:
        raise Exception(f"Error extracting structured data: {str(e)}")


def generate_embedding(text: str) -> list[float]:
    """
    Generate embeddings for text using Google's embedding model.
    
    Args:
        text: Text to generate embedding for (typically experience summary)
        
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
