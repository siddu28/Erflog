"""
Tools for Agent 2: Web Scraper and Search
"""

from tavily import TavilyClient


def search_market_trends(query: str) -> dict:
    """
    Search for market trends using Tavily API
    
    Args:
        query: Search query string
        
    Returns:
        Search results
    """
    client = TavilyClient()
    results = client.search(query, max_results=5)
    return results
