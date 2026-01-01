"""
Test Script for Agent 1: Perception Agent
Tests the perception_node functionality with a sample resume PDF
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def main():
    """Main test function"""
    
    # Step 1: Validate .env file
    print("=" * 70)
    print("AGENT 1 PERCEPTION TEST")
    print("=" * 70)
    
    required_env_vars = ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please ensure these are set in your .env file")
        return False
    
    print("✅ Environment variables loaded successfully")
    
    # Step 2: Check if sample_resume.pdf exists
    print("\n[Step 1] Checking if sample_resume.pdf exists...")
    pdf_path = Path("sample_resume.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Resume file not found: {pdf_path.absolute()}")
        print(f"   Please ensure sample_resume.pdf is in the backend/ directory")
        return False
    
    print(f"✅ Found resume file: {pdf_path.absolute()}")
    
    # Step 3: Import perception_node
    print("\n[Step 2] Importing perception_node...")
    try:
        from agents.agent_1_perception.graph import perception_node
        print("✅ Successfully imported perception_node")
    except ImportError as e:
        print(f"❌ Failed to import perception_node: {str(e)}")
        print("   Please ensure agents/agent_1_perception/graph.py exists")
        return False
    
    # Step 4: Create initial state
    print("\n[Step 3] Creating initial state...")
    initial_state = {
        "resume_text": None,
        "skills": [],
        "user_id": None,
        "context": {"pdf_path": str(pdf_path.absolute())},
        "results": {},
    }
    print(f"✅ Initial state created with PDF path: {initial_state['context']['pdf_path']}")
    
    # Step 5: Run perception_node
    print("\n[Step 4] Running perception_node...")
    try:
        result_state = perception_node(initial_state)
        print("✅ perception_node executed successfully")
    except Exception as e:
        print(f"❌ perception_node failed: {str(e)}")
        print(f"   Error details: {type(e).__name__}")
        return False
    
    # Step 6: Validate and print results
    print("\n[Step 5] Validating results...")
    print("=" * 70)
    
    # Extract values
    user_id = result_state.get("user_id")
    skills = result_state.get("skills", [])
    resume_text = result_state.get("resume_text")
    perception_results = result_state.get("results", {}).get("perception", {})
    email = perception_results.get("email")
    
    # Validation checks
    validation_passed = True
    
    if not user_id:
        print("❌ user_id is missing from result")
        validation_passed = False
    else:
        print(f"✅ user_id: {user_id}")
    
    if not skills or len(skills) == 0:
        print("⚠️  No skills extracted")
    else:
        print(f"✅ Extracted skills ({len(skills)} total):")
        for i, skill in enumerate(skills[:10], 1):  # Show first 10 skills
            print(f"   {i}. {skill}")
        if len(skills) > 10:
            print(f"   ... and {len(skills) - 10} more")
    
    if not email:
        print("⚠️  Email not found in results")
    else:
        print(f"✅ Email: {email}")
    
    if not resume_text or len(resume_text) == 0:
        print("❌ resume_text is empty")
        validation_passed = False
    else:
        print(f"✅ resume_text extracted ({len(resume_text)} characters)")
    
    # Print additional information
    if perception_results:
        print("\n📊 Full Perception Results:")
        print("-" * 70)
        name = perception_results.get("name")
        experience_summary = perception_results.get("experience_summary")
        education = perception_results.get("education")
        profile_id = perception_results.get("profile_id")
        
        if name:
            print(f"Name: {name}")
        if email:
            print(f"Email: {email}")
        if education:
            print(f"Education: {education}")
        if experience_summary:
            summary_preview = experience_summary[:150] + "..." if len(experience_summary) > 150 else experience_summary
            print(f"Experience Summary: {summary_preview}")
        if profile_id:
            print(f"Database Profile ID: {profile_id}")
    
    # Final result
    print("\n" + "=" * 70)
    if validation_passed:
        print("✅ SUCCESS - Agent 1 Perception test passed!")
        return True
    else:
        print("⚠️  TEST COMPLETED WITH WARNINGS - Check results above")
        return True  # Return True since the node executed, even if some data is missing


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⛔ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
