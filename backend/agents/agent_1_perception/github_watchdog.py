"""
Agent 1 Perception - GitHub Watchdog (LangChain Edition)
Analyzes GitHub repositories to verify skills using code evidence.
"""

import os
import base64
from dotenv import load_dotenv
from github import Github

# --- LANGCHAIN IMPORTS ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

def get_latest_user_activity(username_or_token: str):
    """
    Scans the user's GitHub profile to find the ONE repository 
    that was updated most recently.
    """
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token: return None

    try:
        g = Github(token)
        user = g.get_user() # Uses the token's user
        
        # Get repos sorted by 'updated', most recent first
        repos = user.get_repos(sort="updated", direction="desc")
        
        latest_repo = None
        try:
            latest_repo = repos[0]
        except IndexError:
            return None

        # Get latest commit SHA
        try:
            commits = latest_repo.get_commits()
            latest_commit_sha = commits[0].sha
        except:
            latest_commit_sha = "unknown"

        return {
            "repo_name": latest_repo.full_name,
            "repo_url": latest_repo.html_url,
            "last_updated": latest_repo.updated_at.isoformat(),
            "latest_commit_sha": latest_commit_sha
        }

    except Exception as e:
        print(f"❌ GitHub Activity Scan Error: {e}")
        return None

def fetch_and_analyze_github(github_url: str):
    """
    Fetches context (dependencies + recent code) from GitHub 
    and passes it to LangChain for skill analysis.
    """
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token: 
        print("⚠️ GITHUB_ACCESS_TOKEN missing")
        return None

    try:
        g = Github(token)
        clean_url = github_url.rstrip("/")
        parts = clean_url.split("/")
        repo_name = f"{parts[-2]}/{parts[-1]}"
        repo = g.get_repo(repo_name)
        
        context_parts = []
        
        # 1. Dependency Files
        dependency_files = ["requirements.txt", "environment.yml", "package.json", "pyproject.toml", "go.mod", "pom.xml"]
        for dep_file in dependency_files:
            try:
                file_content = repo.get_contents(dep_file)
                decoded = base64.b64decode(file_content.content).decode("utf-8")
                context_parts.append(f"--- DEPENDENCY FILE: {dep_file} ---\n{decoded[:2000]}")
            except: continue 

        # 2. Recent Commits (Last 10)
        commits = repo.get_commits()[:10]
        for commit in commits:
            for file in commit.files:
                if file.filename.endswith(('.py', '.js', '.ts', '.tsx', '.go', '.rs', '.java', '.cpp', '.ipynb')):
                    if file.patch:
                        context_parts.append(f"File: {file.filename}\nChange:\n{file.patch[:1500]}")
                    elif file.filename.endswith(".ipynb"):
                        context_parts.append(f"File: {file.filename} (Jupyter Notebook updated)")

        if not context_parts: 
            print("⚠️ No scannable code found in repo.")
            return None
            
        full_context = "\n\n".join(context_parts)
        
        # Pass to LangChain Analyzer
        return _analyze_robustly(full_context)

    except Exception as e:
        print(f"❌ GitHub Fetch Error: {e}")
        return None

def _analyze_robustly(code_context: str):
    """
    Uses LangChain to extract skills from code context.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    # 1. Setup LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        google_api_key=api_key
    )
    
    # 2. Setup Parser
    parser = JsonOutputParser()
    
    # 3. Setup Prompt
    prompt = PromptTemplate(
        template="""
        You are a Technical Skill Auditor.
        Analyze the following code context (dependency files and recent commits) to identify programming languages, frameworks, and tools used.
        
        Prioritize information found in dependency files (requirements.txt, package.json).
        
        CODE CONTEXT:
        {code_context}
        
        {format_instructions}
        
        Return a JSON object with a key "detected_skills" containing a list of objects with "skill", "level", and "evidence".
        """,
        input_variables=["code_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    # 4. Run Chain
    chain = prompt | llm | parser
    
    try:
        print("[LangChain] Analyzing GitHub Code Context...")
        return chain.invoke({"code_context": code_context})
    except Exception as e:
        print(f"[LangChain] Analysis Error: {e}")
        return None