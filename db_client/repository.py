"""
Repository for interacting with the crawl4ai_site_pages table in Supabase.
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse

from openai import AsyncOpenAI
from supabase import Client

from config import settings
from utils.logging import get_logger
from .client import supabase_client

logger = get_logger(__name__)


class PageRepository:
    """
    Repository for managing crawl4ai_site_pages in Supabase.
    """
    
    def __init__(self, client: Optional[Client] = None):
        """
        Initialize the repository with a Supabase client.
        
        Args:
            client: Optional Supabase client. If not provided, the global client will be used.
        """
        self.client = client or supabase_client.client
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.table_name = "crawl4ai_site_pages"
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text using OpenAI.
        
        Args:
            text: The text to generate an embedding for
            
        Returns:
            The embedding vector
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return a zero vector as fallback
            return [0.0] * 1536
    
    async def save_page(
        self, 
        url: str, 
        content: str, 
        title: str = "", 
        summary: str = "", 
        metadata: Optional[Dict[str, Any]] = None,
        chunk_number: int = 0
    ) -> Dict[str, Any]:
        """
        Save a page to the database.
        
        Args:
            url: The URL of the page
            content: The content of the page
            title: The title of the page
            summary: A summary of the page content
            metadata: Additional metadata for the page
            chunk_number: The chunk number for the page
            
        Returns:
            The saved page data
        """
        try:
            # Generate embedding for the content
            embedding = await self.get_embedding(content)
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            # Add default metadata
            metadata.update({
                "url_path": urlparse(url).path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content)
            })
            
            # Prepare data for insertion
            data = {
                "url": url,
                "chunk_number": chunk_number,
                "title": title,
                "summary": summary,
                "content": content,
                "metadata": metadata,
                "embedding": embedding
            }
            
            # Insert or update the page
            result = self.client.table(self.table_name).upsert(data).execute()
            
            logger.info(f"Saved page: {url} (chunk {chunk_number})")
            return result.data[0] if result.data else {}
            
        except Exception as e:
            logger.error(f"Error saving page {url}: {str(e)}")
            raise
    
    async def get_page(self, url: str, chunk_number: int = 0) -> Optional[Dict[str, Any]]:
        """
        Get a page from the database.
        
        Args:
            url: The URL of the page
            chunk_number: The chunk number for the page
            
        Returns:
            The page data or None if not found
        """
        try:
            result = self.client.table(self.table_name) \
                .select("*") \
                .eq("url", url) \
                .eq("chunk_number", chunk_number) \
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting page {url}: {str(e)}")
            return None
    
    async def delete_page(self, url: str, chunk_number: Optional[int] = None) -> bool:
        """
        Delete a page or all chunks of a page from the database.
        
        Args:
            url: The URL of the page
            chunk_number: Optional chunk number. If not provided, all chunks will be deleted.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = self.client.table(self.table_name).delete().eq("url", url)
            
            if chunk_number is not None:
                query = query.eq("chunk_number", chunk_number)
                
            result = query.execute()
            
            logger.info(f"Deleted page: {url}" + 
                       (f" (chunk {chunk_number})" if chunk_number is not None else " (all chunks)"))
            return True
            
        except Exception as e:
            logger.error(f"Error deleting page {url}: {str(e)}")
            return False
    
    async def search_similar_content(
        self, 
        query: str, 
        limit: int = 5, 
        threshold: float = 0.7,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for pages with similar content using vector similarity.
        
        Args:
            query: The query text
            limit: Maximum number of results to return
            threshold: Similarity threshold (0-1)
            filter_metadata: Optional metadata filter
            
        Returns:
            List of matching pages with similarity scores
        """
        try:
            # Generate embedding for the query
            query_embedding = await self.get_embedding(query)
            
            # Prepare filter
            filter_obj = filter_metadata or {}
            
            # Execute the match_site_pages function
            result = self.client.rpc(
                'match_site_pages',
                {
                    'query_embedding': query_embedding,
                    'match_count': limit,
                    'filter': filter_obj
                }
            ).execute()
            
            # Filter results by threshold
            filtered_results = [
                page for page in result.data 
                if page.get('similarity', 0) >= threshold
            ]
            
            logger.info(f"Found {len(filtered_results)} similar pages for query: {query[:50]}...")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching similar content: {str(e)}")
            return []
    
    async def get_all_urls(self) -> List[str]:
        """
        Get all unique URLs in the database.
        
        Returns:
            List of unique URLs
        """
        try:
            result = self.client.table(self.table_name) \
                .select("url") \
                .execute()
            
            # Extract unique URLs
            urls = list(set(item['url'] for item in result.data))
            return urls
            
        except Exception as e:
            logger.error(f"Error getting all URLs: {str(e)}")
            return []
    
    async def get_page_count(self) -> int:
        """
        Get the total number of pages in the database.
        
        Returns:
            The number of pages
        """
        try:
            result = self.client.table(self.table_name) \
                .select("*", count="exact") \
                .limit(1) \
                .execute()
            
            return result.count or 0
            
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
            return 0
    
    async def get_last_crawled(self, url: str) -> Optional[datetime]:
        """
        Get the last crawled timestamp for a URL.
        
        Args:
            url: The URL to check
            
        Returns:
            The last crawled timestamp or None if not found
        """
        try:
            result = self.client.table(self.table_name) \
                .select("metadata->crawled_at") \
                .eq("url", url) \
                .limit(1) \
                .execute()
            
            if result.data and 'crawled_at' in result.data[0].get('metadata', {}):
                crawled_at = result.data[0]['metadata']['crawled_at']
                return datetime.fromisoformat(crawled_at)
            return None
            
        except Exception as e:
            logger.error(f"Error getting last crawled time for {url}: {str(e)}")
            return None
    
    async def should_update(self, url: str, max_age_days: int = 7) -> bool:
        """
        Check if a page should be updated based on its last crawled timestamp.
        
        Args:
            url: The URL to check
            max_age_days: Maximum age in days before a page should be updated
            
        Returns:
            True if the page should be updated, False otherwise
        """
        last_crawled = await self.get_last_crawled(url)
        
        # If never crawled, should update
        if last_crawled is None:
            return True
        
        # Check if the page is older than max_age_days
        now = datetime.now(timezone.utc)
        age = now - last_crawled
        
        return age.days >= max_age_days
