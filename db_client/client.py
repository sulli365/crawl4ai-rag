"""
Supabase client for the crawl4ai-rag application.
"""

import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client

from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


class SupabaseClient:
    """
    Singleton class for managing Supabase client connection.
    """
    _instance: Optional["SupabaseClient"] = None
    _client: Optional[Client] = None
    
    def __new__(cls) -> "SupabaseClient":
        """Ensure only one instance of the client exists."""
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance
    
    def _initialize_client(self) -> None:
        """Initialize the Supabase client."""
        try:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def health_check(self) -> bool:
        """
        Check if the Supabase connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        try:
            # Simple query to check connection
            self.client.table("crawl4ai_site_pages").select("count(*)", count="exact").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {str(e)}")
            return False


# Create a global instance of the Supabase client
supabase_client = SupabaseClient()
