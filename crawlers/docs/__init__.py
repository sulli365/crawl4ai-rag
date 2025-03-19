"""
Documentation website crawler for the crawl4ai documentation.
"""

import os
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from ...config import settings
from ...utils.logging import get_logger
from ...supabase.repository import PageRepository

logger = get_logger(__name__)


def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """
    Split text into chunks, respecting code blocks and paragraphs.
    
    Args:
        text: The text to split
        chunk_size: Maximum size of each chunk
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif '\n\n' in chunk:
            # Find the last paragraph break
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif '. ' in chunk:
            # Find the last sentence break
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_period + 1

        # Extract chunk and clean it up
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position for next chunk
        start = max(start + 1, end)

    return chunks


async def get_title_and_summary(chunk: str, url: str, openai_client) -> Dict[str, str]:
    """
    Extract title and summary using OpenAI.
    
    Args:
        chunk: The text chunk
        url: The URL of the page
        openai_client: The OpenAI client
        
    Returns:
        Dictionary with title and summary
    """
    system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    try:
        response = await openai_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"URL: {url}\n\nContent:\n{chunk[:1000]}..."}  # Send first 1000 chars for context
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error getting title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}


class DocumentationCrawler:
    """
    Crawler for the crawl4ai documentation website.
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize the documentation crawler.
        
        Args:
            base_url: The base URL of the documentation website
        """
        self.base_url = base_url or settings.docs_url
        self.page_repo = PageRepository()
        
        # Configure browser
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        
        # Configure crawler
        self.crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            excluded_tags=['form', 'header'],
            exclude_external_links=True,
            process_iframes=True,
            remove_overlay_elements=True,
        )
    
    async def get_sitemap_urls(self) -> List[str]:
        """
        Get URLs from the sitemap.
        
        Returns:
            List of URLs
        """
        sitemap_url = urljoin(self.base_url, "/sitemap.xml")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(sitemap_url)
                response.raise_for_status()
                
                # Parse the XML
                root = ElementTree.fromstring(response.content)
                
                # Extract all URLs from the sitemap
                namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
                
                logger.info(f"Found {len(urls)} URLs in sitemap")
                return urls
                
        except Exception as e:
            logger.error(f"Error fetching sitemap: {e}")
            return []
    
    async def crawl_url(self, url: str) -> Optional[str]:
        """
        Crawl a single URL and return its markdown content.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Markdown content or None if failed
        """
        try:
            # Create the crawler instance
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                # Crawl the URL
                result = await crawler.arun(
                    url=url,
                    config=self.crawl_config
                )
                
                if result.success:
                    logger.info(f"Successfully crawled: {url}")
                    return result.markdown_v2.raw_markdown
                else:
                    logger.error(f"Failed to crawl {url}: {result.error_message}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return None
    
    async def process_and_store_document(self, url: str, markdown: str, openai_client) -> int:
        """
        Process a document and store its chunks in the database.
        
        Args:
            url: The URL of the document
            markdown: The markdown content
            openai_client: The OpenAI client
            
        Returns:
            Number of chunks stored
        """
        try:
            # Split into chunks
            chunks = chunk_text(markdown)
            
            # Process chunks
            for i, chunk in enumerate(chunks):
                # Get title and summary
                title_summary = await get_title_and_summary(chunk, url, openai_client)
                
                # Extract title and summary
                title = title_summary.get("title", f"Chunk {i+1} of {url}")
                summary = title_summary.get("summary", "No summary available")
                
                # Create metadata
                metadata = {
                    "source": "crawl4ai_docs",
                    "chunk_size": len(chunk),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "url_path": urlparse(url).path
                }
                
                # Save to database
                await self.page_repo.save_page(
                    url=url,
                    content=chunk,
                    title=title,
                    summary=summary,
                    metadata=metadata,
                    chunk_number=i
                )
                
                logger.info(f"Processed chunk {i+1}/{len(chunks)} for {url}")
            
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error processing document {url}: {str(e)}")
            return 0
    
    async def crawl_parallel(self, urls: List[str], max_concurrent: int = 5, openai_client = None) -> int:
        """
        Crawl multiple URLs in parallel with a concurrency limit.
        
        Args:
            urls: List of URLs to crawl
            max_concurrent: Maximum number of concurrent crawls
            openai_client: The OpenAI client
            
        Returns:
            Number of documents processed
        """
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_url(url: str) -> int:
            async with semaphore:
                # Check if we should update this URL
                should_update = await self.page_repo.should_update(url)
                
                if not should_update:
                    logger.info(f"Skipping {url} - recently crawled")
                    return 0
                
                # Crawl the URL
                markdown = await self.crawl_url(url)
                
                if markdown:
                    # Process and store the document
                    return await self.process_and_store_document(url, markdown, openai_client)
                return 0
        
        # Process all URLs in parallel with limited concurrency
        results = await asyncio.gather(*[process_url(url) for url in urls])
        
        # Count total chunks processed
        total_chunks = sum(results)
        
        logger.info(f"Processed {total_chunks} chunks from {len(urls)} URLs")
        return total_chunks
    
    async def crawl_documentation(self, max_concurrent: int = 5, openai_client = None) -> int:
        """
        Crawl the entire documentation website.
        
        Args:
            max_concurrent: Maximum number of concurrent crawls
            openai_client: The OpenAI client
            
        Returns:
            Number of documents processed
        """
        logger.info(f"Starting crawl of documentation: {self.base_url}")
        
        try:
            # Get URLs from sitemap
            urls = await self.get_sitemap_urls()
            
            if not urls:
                logger.warning("No URLs found in sitemap")
                return 0
            
            # Crawl URLs in parallel
            return await self.crawl_parallel(urls, max_concurrent, openai_client)
            
        except Exception as e:
            logger.error(f"Error crawling documentation: {str(e)}")
            return 0


async def crawl_documentation_website(
    base_url: str = None,
    max_concurrent: int = 5,
    openai_client = None
) -> int:
    """
    Crawl the crawl4ai documentation website and save pages to the database.
    
    Args:
        base_url: The base URL of the documentation website
        max_concurrent: Maximum number of concurrent crawls
        openai_client: The OpenAI client
        
    Returns:
        Number of documents processed
    """
    crawler = DocumentationCrawler(base_url)
    return await crawler.crawl_documentation(max_concurrent, openai_client)
