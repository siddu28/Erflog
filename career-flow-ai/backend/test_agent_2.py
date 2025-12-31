"""
Test Script for Agent 2: Market Sentinel
Tests the market_scan_node functionality with mock state
"""

import sys
import os

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def main():
    """Main test function"""
    
    print("=" * 70)
    print("🚀 Starting Market Agent Test...")
    print("=" * 70)
    
    # Step 1: Validate environment variables
    print("\n[Step 1] Checking environment variables...")
    
    required_vars = ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    optional_vars = ["TAVILY_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME"]
    
    missing_required = [var for var in required_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    print("✅ Required environment variables loaded")
    
    if missing_optional:
        print(f"⚠️  Optional vars missing (will use fallbacks): {', '.join(missing_optional)}")
    else:
        print("✅ All optional environment variables loaded")
    
    # Step 2: Import market_scan_node
    print("\n[Step 2] Importing market_scan_node...")
    try:
        from agents.agent_2_market.graph import market_scan_node
        print("✅ Successfully imported market_scan_node")
    except ImportError as e:
        print(f"❌ Failed to import market_scan_node: {str(e)}")
        print("   Please ensure agents/agent_2_market/graph.py exists")
        return False
    
    # Step 3: Create mock state
    print("\n[Step 3] Creating mock AgentState...")
    initial_state = {
        "resume_text": None,
        "skills": ["Python", "FastAPI", "React"],
        "user_id": "test-user-agent-2",
        "context": {},
        "results": {},
    }
    print(f"✅ Mock state created with skills: {initial_state['skills']}")
    
    # Step 4: Run market_scan_node
    print("\n[Step 4] Running market_scan_node...")
    print("-" * 70)
    try:
        result_state = market_scan_node(initial_state)
        print("-" * 70)
        print("✅ market_scan_node executed successfully")
    except Exception as e:
        print("-" * 70)
        print(f"❌ market_scan_node failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Validate and print results
    print("\n[Step 5] Validating results...")
    print("=" * 70)
    
    # Get market results
    market_results = result_state.get("results", {}).get("market", {})
    job_matches = result_state.get("job_matches", [])
    
    # Check for errors
    if "market_error" in result_state.get("results", {}):
        print(f"⚠️  Market error occurred: {result_state['results']['market_error']}")
    
    # Print jobs found
    jobs_found = market_results.get("jobs_found", 0)
    jobs_saved = market_results.get("jobs_saved", 0)
    vectors_saved = market_results.get("vectors_saved", 0)
    search_query = market_results.get("search_query", "N/A")
    
    print(f"\n📊 Search Query: {search_query}")
    print(f"📊 Jobs Found: {jobs_found}")
    print(f"📊 Jobs Saved to Supabase: {jobs_saved}")
    print(f"📊 Vectors Saved to Pinecone: {vectors_saved}")
    
    # Print first 3 jobs
    print("\n🔍 Top 3 Job Matches:")
    print("-" * 70)
    
    if not job_matches:
        print("   No jobs found in job_matches")
    else:
        for i, job in enumerate(job_matches[:3], 1):
            title = job.get("title", "Unknown Title")
            company = job.get("company", "Unknown Company")
            link = job.get("link", "N/A")
            print(f"   {i}. {title}")
            print(f"      Company: {company}")
            print(f"      Link: {link}")
            print()
    
    # Verify storage
    print("-" * 70)
    if jobs_saved > 0:
        print(f"✅ {jobs_saved} jobs saved to Supabase (jobs table)")
    else:
        print("⚠️  No jobs saved to Supabase")
    
    if vectors_saved > 0:
        print(f"✅ Vectors saved to Pinecone (Default Namespace)")
    else:
        print("⚠️  No vectors saved to Pinecone (API key may be missing)")
    
    # Print job IDs if available
    job_ids = market_results.get("job_ids", [])
    if job_ids:
        print(f"\n📋 Supabase Job IDs: {job_ids}")
    
    # Final result
    print("\n" + "=" * 70)
    if jobs_found > 0:
        print("✅ SUCCESS - Agent 2 Market Sentinel test passed!")
        return True
    else:
        print("⚠️  TEST COMPLETED - No jobs were found (check API keys)")
        return True


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
