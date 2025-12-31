"""
Database Connection Module - Supabase Integration
"""

from os import getenv
from supabase import create_client, Client


class DatabaseManager:
    """Manages Supabase database connections."""
    
    def __init__(self):
        """Initialize database client from environment variables."""
        url = getenv("SUPABASE_URL")
        key = getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        
        self.client: Client = create_client(url, key)
    
    def get_client(self) -> Client:
        """Get the Supabase client."""
        return self.client


# Global instance
db_manager = DatabaseManager()
