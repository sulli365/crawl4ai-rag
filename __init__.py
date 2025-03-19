"""
crawl4ai-rag: Agentic RAG application for crawl4ai.

This package provides functionality to:
1. Analyze websites and generate Python code for scraping
2. Export website content as markdown files
3. Sync crawl4ai GitHub repository and documentation to Supabase
"""

from typing import Dict, List, Any, Optional, Union

from .analyzer import analyze_website, detect_website_type
from .codegen import generate_code
from .exporters import export_markdown
from .crawlers import update_sources
from .config import settings

__version__ = "0.1.0"
__all__ = [
    "analyze_and_generate",
    "analyze_website",
    "detect_website_type",
    "generate_code",
    "export_markdown",
    "update_sources",
    "settings"
]


async def analyze_and_generate(
    urls: Union[str, List[str]],
    purpose: str,
    output_code: bool = True,
    output_markdown: bool = False,
    markdown_output_dir: Optional[str] = None,
    website_type: Optional[str] = None,
    max_depth: int = 1,
    max_urls: int = 10
) -> Dict[str, Any]:
    """
    Analyze websites and generate code/markdown based on purpose.
    
    Args:
        urls: URL or list of URLs to analyze
        purpose: Description of scraping purpose
        output_code: Whether to return generated code
        output_markdown: Whether to generate markdown
        markdown_output_dir: Directory to write markdown files (if None, returns content)
        website_type: Type of website (if None, auto-detect)
        max_depth: Maximum crawl depth
        max_urls: Maximum number of URLs to analyze
        
    Returns:
        Dictionary containing generated code and/or paths to markdown files
    """
    # Convert single URL to list
    if isinstance(urls, str):
        urls = [urls]
    
    result = {
        "urls": urls,
        "purpose": purpose
    }
    
    # Process first URL (main URL)
    main_url = urls[0]
    
    # Analyze website
    analysis = await analyze_website(
        url=main_url,
        website_type=website_type,
        max_depth=max_depth,
        max_urls=max_urls
    )
    
    result["analysis"] = analysis
    result["website_type"] = analysis.get("website_type", "generic")
    
    # Generate code if requested
    if output_code:
        code = await generate_code(
            url=main_url,
            purpose=purpose,
            website_type=website_type
        )
        result["code"] = code
    
    # Generate markdown if requested
    if output_markdown:
        markdown_files = await export_markdown(
            url=main_url,
            output_dir=markdown_output_dir,
            website_type=website_type,
            max_depth=max_depth,
            max_urls=max_urls
        )
        result["markdown_files"] = markdown_files
    
    return result
