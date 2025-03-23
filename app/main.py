"""
Main application module for crawl4ai-rag.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

from analyzer.website_analyzer import WebsiteAnalyzer
from analyzer.github_mcp import sync_github_repository
from db_client.repository import PageRepository
from .generator import generate_scraper_code

app = FastAPI(
    title="Crawl4AI RAG",
    description="Code generation API using Crawl4AI documentation",
    version="0.1.0"
)


class ScraperRequest(BaseModel):
    query: str  # User request (e.g., "Extract article titles and links from TechCrunch")


class ScraperResponse(BaseModel):
    generated_code: str


@app.post("/generate_scraper/", response_model=ScraperResponse)
async def generate_scraper(request: ScraperRequest):
    """Generate Crawl4AI scraper code based on user request."""
    try:
        code = generate_scraper_code(request.query)
        return {"generated_code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_and_generate(
    urls: List[str],
    purpose: str,
    output_code: bool = True,
    output_markdown: bool = False,
    markdown_output_dir: Optional[str] = None,
    use_mcp: bool = True
) -> Dict[str, Any]:
    """
    Analyze websites and generate code/markdown based on purpose.
    
    Args:
        urls: List of URLs to analyze
        purpose: Description of scraping purpose
        output_code: Whether to return generated code
        output_markdown: Whether to generate markdown
        markdown_output_dir: Directory to write markdown files (if None, returns content)
        use_mcp: Whether to use MCP servers for content retrieval
        
    Returns:
        Dictionary containing generated code and/or paths to markdown files
    """
    try:
        # Initialize analyzer
        analyzer = WebsiteAnalyzer(use_mcp=use_mcp)
        
        # Analyze websites
        analysis_results = []
        for url in urls:
            # Check if this is a GitHub URL
            parsed_url = urlparse(url)
            is_github = parsed_url.netloc == "github.com" or parsed_url.netloc.endswith(".github.com")
            
            if is_github and use_mcp:
                # Use GitHub-specific analysis
                from analyzer.strategies.github_strategy import GitHubDocumentationStrategy
                github_strategy = GitHubDocumentationStrategy()
                result = await github_strategy.analyze_repository(url)
                result["root_url"] = url
                result["purpose"] = purpose
            else:
                # Use general website analysis
                result = await analyzer.analyze_website(url, purpose)
            
            analysis_results.append(result)
        
        # Generate code if requested
        code = None
        if output_code:
            code = await analyzer.generate_code(analysis_results[0])
        
        # Generate markdown if requested
        markdown_files = []
        if output_markdown:
            if markdown_output_dir:
                os.makedirs(markdown_output_dir, exist_ok=True)
            
            for result in analysis_results:
                markdown = await analyzer.generate_markdown(result)
                
                if markdown_output_dir:
                    # Write to file
                    url = result.get("root_url", "unknown")
                    parsed = urlparse(url)
                    filename = f"{parsed.netloc.replace('.', '_')}_{parsed.path.replace('/', '_')}.md"
                    filepath = os.path.join(markdown_output_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(markdown)
                    
                    markdown_files.append(filepath)
                else:
                    # Return content
                    markdown_files.append(markdown)
        
        # Prepare result
        result = {}
        if output_code:
            result["code"] = code
        if output_markdown:
            result["markdown_files"] = markdown_files
        
        return result
        
    except Exception as e:
        logger.error(f"Error in analyze_and_generate: {str(e)}")
        return {"error": str(e)}


async def sync_website_to_supabase(
    url: str,
    max_depth: int = 2,
    force_update: bool = False,
    use_mcp: bool = True
) -> int:
    """
    Crawl website and sync pages to Supabase.
    
    Args:
        url: Root URL to crawl
        max_depth: Maximum crawl depth
        force_update: Whether to update existing pages
        use_mcp: Whether to use MCP servers for content retrieval
        
    Returns:
        Number of pages synced
    """
    try:
        # Check if this is a GitHub URL
        parsed_url = urlparse(url)
        is_github = parsed_url.netloc == "github.com" or parsed_url.netloc.endswith(".github.com")
        
        if is_github and use_mcp:
            # Use GitHub-specific sync
            path_parts = parsed_url.path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1]
                
                # Determine branch
                branch = "main"  # Default branch
                if len(path_parts) > 4 and path_parts[2] == "tree":
                    branch = path_parts[3]
                
                # Sync GitHub repository
                return await sync_github_repository(
                    owner=owner,
                    repo=repo,
                    branch=branch,
                    include_issues=False,
                    include_pull_requests=False
                )
            else:
                raise ValueError(f"Invalid GitHub URL: {url}")
        else:
            # Use general website sync
            # This is a placeholder for the general website sync implementation
            # In a real implementation, you would use crawl4ai to crawl the website
            # and sync the pages to Supabase
            logger.warning("General website sync not implemented yet")
            return 0
        
    except Exception as e:
        logger.error(f"Error in sync_website_to_supabase: {str(e)}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
