"""
Test script for GitHub MCP integration.
"""

import asyncio
import os
import sys

from analyzer.github_mcp import sync_github_repository
from utils.logging import setup_logging

setup_logging()

async def test_github_mcp():
    """
    Test GitHub MCP integration with the crawl4ai repository.
    """
    owner = "unclecode"
    repo = "crawl4ai"
    
    print(f"Testing GitHub MCP integration with {owner}/{repo}")
    
    count = await sync_github_repository(
        owner=owner,
        repo=repo,
        branch="main",
        include_issues=False,
        include_pull_requests=False
    )
    
    print(f"Synced {count} items from GitHub repository {owner}/{repo} to Supabase")

if __name__ == "__main__":
    asyncio.run(test_github_mcp())
