"""
Supabase integration for the crawl4ai-rag application.
"""

from .client import SupabaseClient, supabase_client
from .repository import PageRepository

__all__ = ["SupabaseClient", "supabase_client", "PageRepository"]
