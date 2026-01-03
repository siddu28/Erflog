import requests
import os
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
RESUME_PATH = "sample_resume.pdf"  # Ensure this file exists in the same folder

def print_section(title):
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def main():
    session_id = None

    # ---------------------------------------------------------
    # 1. Initialize Session
    # ---------------------------------------------------------
    print_section("Step 1: Initializing Session")
    try:
        response = requests.post(f"{BASE_URL}/api/init")
        response.raise_for_status()
        data = response.json()
        session_id = data.get("session_id")
        print(f"✅ Session Created: {session_id}")
        print(f"   Message: {data.get('message')}")
    except Exception as e:
        print(f"❌ Failed to init session: {e}")
        return

    # ---------------------------------------------------------
    # 2. Upload Resume (Agent 1: Perception)
    # ---------------------------------------------------------
    print_section("Step 2: Uploading Resume (Agent 1: Perception)")
    if not os.path.exists(RESUME_PATH):
        print(f"❌ Error: {RESUME_PATH} not found! Please create a dummy PDF.")
        return
        
    try:
        with open(RESUME_PATH, "rb") as f:
            files = {"file": (RESUME_PATH, f, "application/pdf")}
            data = {"session_id": session_id}
            
            response = requests.post(
                f"{BASE_URL}/api/upload-resume", 
                data=data, 
                files=files
            )
        
        response.raise_for_status()
        json_resp = response.json()
        
        profile = json_resp.get("profile", {})
        print(f"✅ Resume Parsed!")
        print(f"   Name: {profile.get('name')}")
        print(f"   Email: {profile.get('email')}")
        skills = profile.get('skills', [])
        if skills:
            print(f"   Skills: {skills[:5]}{'...' if len(skills) > 5 else ''}")
        else:
            print(f"   Skills: None extracted")
        print(f"   User ID: {profile.get('user_id')}")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Agent 1 Failed (HTTP {response.status_code}): {e}")
        print(f"   Response: {response.text}")
        return
    except Exception as e:
        print(f"❌ Agent 1 Failed: {e}")
        return

    # ---------------------------------------------------------
    # 3. Market Scan (Agent 2: Market Sentinel)
    # ---------------------------------------------------------
    print_section("Step 3: Scanning Market (Agent 2: Market Sentinel)")
    try:
        response = requests.post(
            f"{BASE_URL}/api/market-scan", 
            json={"session_id": session_id}
        )
        response.raise_for_status()
        json_resp = response.json()
        
        jobs = json_resp.get("job_matches", [])
        print(f"✅ Found {json_resp.get('total_matches', len(jobs))} Jobs")
        
        if jobs:
            for i, job in enumerate(jobs[:3], 1):
                print(f"   {i}. {job.get('title')} @ {job.get('company')}")
        else:
            print("   No jobs found (this may be expected if Tavily API is not configured)")
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Agent 2 Failed (HTTP {response.status_code}): {e}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Agent 2 Failed: {e}")

    # ---------------------------------------------------------
    # 4. Generate Strategy (Agent 3: Strategist)
    # ---------------------------------------------------------
    print_section("Step 4: Generating Strategy (Agent 3: Strategist)")
    try:
        response = requests.post(
            f"{BASE_URL}/api/generate-strategy", 
            json={"session_id": session_id}
        )
        response.raise_for_status()
        json_resp = response.json()
        
        strategy = json_resp.get("strategy", {})
        matched_jobs = strategy.get("matched_jobs", [])
        recommendations = strategy.get("recommendations", [])
        
        print(f"✅ Strategy Generated!")
        print(f"   Total Matches: {strategy.get('total_matches', 0)}")
        
        if matched_jobs:
            print(f"   Top Matches:")
            for i, job in enumerate(matched_jobs[:3], 1):
                score = job.get('score', 0)
                print(f"      {i}. {job.get('title')} @ {job.get('company')} (Score: {score:.2f})")
        
        if recommendations:
            print(f"   Recommendations:")
            for rec in recommendations:
                print(f"      - {rec}")
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Agent 3 Failed (HTTP {response.status_code}): {e}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Agent 3 Failed: {e}")

    # ---------------------------------------------------------
    # 5. Generate Application (Agent 4: Operative)
    # ---------------------------------------------------------
    print_section("Step 5: Tailoring Application (Agent 4: Operative)")
    try:
        # Provide a job description if none was found from previous steps
        payload = {"session_id": session_id}
        
        response = requests.post(
            f"{BASE_URL}/api/generate-application", 
            json=payload
        )
        response.raise_for_status()
        json_resp = response.json()
        
        app_data = json_resp.get("application", {})
        
        # Debug: Print full response if needed
        # print(f"   DEBUG Full Response: {json.dumps(json_resp, indent=2)}")
        
        pdf_path = app_data.get('pdf_path')
        pdf_url = app_data.get('pdf_url')  # Supabase storage URL
        recruiter_email = app_data.get('recruiter_email')
        status = app_data.get('application_status')
        rewritten = app_data.get('rewritten_content')
        
        print(f"✅ Application Ready!")
        # pdf_url is the Supabase storage URL (this is what you see in Postman)
        if pdf_url:
            print(f"   PDF URL (Supabase): {pdf_url}")
        elif pdf_path:
            print(f"   PDF Path (Local): {pdf_path}")
        else:
            print(f"   PDF: Not generated (check server logs)")
        print(f"   Recruiter Email: {recruiter_email if recruiter_email and 'None' not in str(recruiter_email) else 'Not found'}")
        print(f"   Status: {status if status else 'Unknown'}")
        
        # Show rewritten content summary if available
        if rewritten:
            if isinstance(rewritten, dict):
                print(f"   Rewritten Summary: {rewritten.get('summary', 'N/A')[:100]}...")
            else:
                print(f"   Rewritten Content: Available")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Agent 4 Failed (HTTP {response.status_code}): {e}")
        print(f"   Response: {response.text}")
        
        # Try with a sample job description
        print("\n   Retrying with sample job description...")
        try:
            payload = {
                "session_id": session_id,
                "job_description": "Senior Software Engineer at TechCorp. Requirements: Python, FastAPI, AWS, 5+ years experience."
            }
            response = requests.post(
                f"{BASE_URL}/api/generate-application", 
                json=payload
            )
            response.raise_for_status()
            json_resp = response.json()
            app_data = json_resp.get("application", {})
            print(f"   ✅ Retry Success!")
            print(f"      PDF Path: {app_data.get('pdf_path') or 'Not generated'}")
            print(f"      Status: {app_data.get('application_status') or 'Unknown'}")
        except Exception as retry_e:
            print(f"   ❌ Retry also failed: {retry_e}")
            
    except Exception as e:
        print(f"❌ Agent 4 Failed: {e}")

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------
    print_section("Test Complete!")
    print("Check the server logs for detailed agent output.")

if __name__ == "__main__":
    main()