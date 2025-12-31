import requests
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000"
RESUME_PATH = "sample_resume.pdf"

def print_section(title):
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def main():
    # 1. Initialize Session
    print_section("Step 1: Initializing Session")
    try:
        response = requests.post(f"{BASE_URL}/api/init")
        response.raise_for_status()
        session_id = response.json()["session_id"]
        print(f"✅ Session Created: {session_id}")
    except Exception as e:
        print(f"❌ Failed to init session: {e}")
        return

    # 2. Upload Resume (Agent 1: Perception)
    print_section("Step 2: Uploading Resume (Agent 1: Perception)")
    if not os.path.exists(RESUME_PATH):
        print(f"❌ Error: {RESUME_PATH} not found!")
        return
        
    try:
        with open(RESUME_PATH, "rb") as f:
            files = {"file": f}
            # FIX 1: Send session_id as 'data' (Form Data), not 'params'
            response = requests.post(
                f"{BASE_URL}/api/upload-resume", 
                data={"session_id": session_id}, 
                files=files
            )
        
        # Fallback: If 422, try query param (depends on how Copilot wrote it)
        if response.status_code == 422:
             with open(RESUME_PATH, "rb") as f:
                response = requests.post(
                    f"{BASE_URL}/api/upload-resume", 
                    params={"session_id": session_id}, 
                    files={"file": f}
                )

        response.raise_for_status()
        data = response.json()
        print(f"✅ Resume Parsed!")
        print(f"   Name: {data.get('name')}")
    except Exception as e:
        print(f"❌ Agent 1 Failed: {e}")
        print(f"   Response Text: {response.text}")

    # 3. Market Scan (Agent 2: Market Sentinel)
    print_section("Step 3: Scanning Market (Agent 2: Market Sentinel)")
    try:
        # FIX 2: Send session_id as JSON body
        response = requests.post(
            f"{BASE_URL}/api/market-scan", 
            json={"session_id": session_id}
        )
        
        # Fallback for query param style
        if response.status_code == 422:
            response = requests.post(
                f"{BASE_URL}/api/market-scan", 
                params={"session_id": session_id}
            )

        response.raise_for_status()
        jobs = response.json()
        print(f"✅ Found {len(jobs)} Jobs")
        if jobs:
            print(f"   Top Match: {jobs[0]['title']} @ {jobs[0]['company']}")
    except Exception as e:
        print(f"❌ Agent 2 Failed: {e}")
        print(f"   Response Text: {response.text}")

    # 4. Generate Strategy (Agent 3: Strategist)
    print_section("Step 4: Generating Strategy (Agent 3: Strategist)")
    try:
        # FIX 3: Send session_id as JSON body
        response = requests.post(
            f"{BASE_URL}/api/generate-strategy", 
            json={"session_id": session_id}
        )
        
        if response.status_code == 422:
             response = requests.post(
                f"{BASE_URL}/api/generate-strategy", 
                params={"session_id": session_id}
            )

        response.raise_for_status()
        strategy = response.json()
        print(f"✅ Strategy Generated!")
        print(f"   Match Score: {strategy.get('analysis', {}).get('match_score')}/100")
    except Exception as e:
        print(f"❌ Agent 3 Failed: {e}")
        print(f"   Response Text: {response.text}")

    # 5. Generate Application (Agent 4: Operative)
    print_section("Step 5: Tailoring Application (Agent 4: Operative)")
    try:
        # FIX 4: Send session_id as JSON body
        response = requests.post(
            f"{BASE_URL}/api/generate-application", 
            json={"session_id": session_id}
        )

        if response.status_code == 422:
             response = requests.post(
                f"{BASE_URL}/api/generate-application", 
                params={"session_id": session_id}
            )

        response.raise_for_status()
        app_data = response.json()
        print(f"✅ Application Ready!")
        print(f"   Recruiter Email: {app_data.get('recruiter_email')}")
    except Exception as e:
        print(f"❌ Agent 4 Failed: {e}")
        print(f"   Response Text: {response.text}")

if __name__ == "__main__":
    main()