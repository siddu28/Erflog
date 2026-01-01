# backend/agents/agent_1_perception/github_watchdog.py

import os
import json
import base64
import google.generativeai as genai
from dotenv import load_dotenv
from github import Github

# Load env vars
load_dotenv()

# Configure Google AI
api_key = os.getenv("GEMINI_API_KEY") 
if not api_key:
    api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# Fail-safe model list
MODELS_TO_TRY = [
    "gemini-2.5-flash"
]

def fetch_and_analyze_github(github_url: str):
    """
    1. Connects to GitHub.
    2. SMART SCAN: Fetches dependency files (requirements.txt, package.json).
    3. DEEP SCAN: Fetches recent code commits (including .ipynb).
    4. Sends combined context to Gemini.
    """
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token:
        print("⚠️ No GITHUB_ACCESS_TOKEN found in .env")
        return None

    try:
        g = Github(token)
        
        # Parse URL
        clean_url = github_url.rstrip("/")
        parts = clean_url.split("/")
        repo_name = f"{parts[-2]}/{parts[-1]}"
        
        print(f"👀 Watchdog connecting to: {repo_name}")
        repo = g.get_repo(repo_name)
        
        context_parts = []

        # --- STRATEGY 1: DEPENDENCY SCAN (Gold Standard) ---
        # We explicitly look for these files because they list EVERY skill.
        dependency_files = ["requirements.txt", "environment.yml", "Pipfile", "pyproject.toml", "package.json"]
        
        for dep_file in dependency_files:
            try:
                file_content = repo.get_contents(dep_file)
                decoded = base64.b64decode(file_content.content).decode("utf-8")
                # Truncate if huge
                context_parts.append(f"--- DEPENDENCY FILE: {dep_file} ---\n{decoded[:2000]}")
                print(f"✅ Found dependency file: {dep_file}")
            except:
                continue # File doesn't exist, skip

        # --- STRATEGY 2: RECENT COMMITS (Activity Scan) ---
        commits = repo.get_commits()[:10]
        for commit in commits:
            for file in commit.files:
                if file.filename.endswith(('.py', '.js', '.ts', '.tsx', '.go', '.rs', '.java', '.cpp', '.ipynb')):
                    # If patch exists, use it. If not (large file), try to infer from filename
                    if file.patch:
                        context_parts.append(f"File: {file.filename}\nChange:\n{file.patch[:1500]}")
                    elif file.filename.endswith(".ipynb"):
                        context_parts.append(f"File: {file.filename} (Jupyter Notebook updated - implies Data Science work)")

        if not context_parts:
            print("⚠️ No dependencies or code changes found.")
            return None

        full_context = "\n\n".join(context_parts)
        
        return _analyze_robustly(full_context)

    except Exception as e:
        print(f"❌ GitHub Watchdog System Error: {e}")
        return None

def _analyze_robustly(code_context: str):
    """
    Loops through models to find one that works.
    """
    prompt = f"""
    You are a Technical Skill Auditor.
    Below is context from a GitHub repository (Dependency files + Recent Code).
    
    CODE CONTEXT:
    {code_context}
    
    TASK:
    1. Analyize the 'DEPENDENCY FILES' first. They list the exact libraries used.
       - 'pandas', 'numpy', 'sklearn', 'matplotlib' -> Data Science / Machine Learning.
       - 'react', 'next' -> Frontend Development.
       - 'fastapi', 'django' -> Backend Development.
    2. Look at code changes for usage evidence.
    3. Output a STRICT JSON object.
    
    OUTPUT JSON FORMAT:
    {{
        "detected_skills": [
            {{ "skill": "Pandas", "level": "Intermediate", "evidence": "Found in requirements.txt" }},
            {{ "skill": "Scikit-Learn", "level": "Intermediate", "evidence": "Found in requirements.txt" }}
        ]
    }}
    """

    for model_name in MODELS_TO_TRY:
        try:
            print(f"🤖 Analyzing with model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)

        except Exception as e:
            print(f"⚠️ {model_name} failed, trying next...")
            continue
            
    print("❌ All Gemini models failed.")
    return None