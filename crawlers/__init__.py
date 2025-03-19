"""
Crawlers for the crawl4ai-rag application.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple

from openai import AsyncOpenAI

from ..config import settings
from ..utils.logging import get_logger
from .github import crawl_github_repository
from .docs import crawl_documentation_website

logger = get_logger(__name__)


async def crawl_all_sources(
    github_repo: Optional[str] = None,
    github_token: Optional[str] = None,
    docs_url: Optional[str] = None,
    max_concurrent: int = 5,
    force_update: bool = False
) -> Dict[str, int]:
    """
    Crawl all sources (GitHub repository and documentation website).
    
    Args:
        github_repo: The GitHub repository to crawl (owner/repo)
        github_token: GitHub API token for authentication
        docs_url: The documentation website URL
        max_concurrent: Maximum number of concurrent crawls
        force_update: Whether to force update existing pages
        
    Returns:
        Dictionary with counts of processed documents for each source
    """
    logger.info("Starting crawl of all sources")
    
    # Initialize OpenAI client
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Use default values if not provided
    github_repo = github_repo or settings.github_repo
    docs_url = docs_url or settings.docs_url
    
    # Crawl GitHub repository and documentation website in parallel
    github_task = asyncio.create_task(
        crawl_github_repository(
            repo=github_repo,
            token=github_token,
            max_depth=3
        )
    )
    
    docs_task = asyncio.create_task(
        crawl_documentation_website(
            base_url=docs_url,
            max_concurrent=max_concurrent,
            openai_client=openai_client
        )
    )
    
    # Wait for both tasks to complete
    github_count, docs_count = await asyncio.gather(github_task, docs_task)
    
    result = {
        "github": github_count,
        "docs": docs_count,
        "total": github_count + docs_count
    }
    
    logger.info(f"Completed crawl of all sources: {result}")
    return result


async def update_sources(
    force_update: bool = False,
    max_concurrent: int = 5
) -> Dict[str, int]:
    """
    Update all sources if needed.
    
    Args:
        force_update: Whether to force update existing pages
        max_concurrent: Maximum number of concurrent crawls
        
    Returns:
        Dictionary with counts of processed documents for each source
    """
    return await crawl_all_sources(
        max_concurrent=max_concurrent,
        force_update=force_update
    )
