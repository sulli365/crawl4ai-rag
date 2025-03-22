"""
Command-line interface for the crawl4ai-rag application.
"""

import asyncio
import sys
import os
from typing import List, Optional, Dict, Any
import typer
from enum import Enum

from config import settings
from utils.logging import setup_logging, get_logger
from analyzer import analyze_website, detect_website_type
from codegen import generate_code
from exporters import export_markdown
from crawlers import update_sources

# Initialize logger
logger = get_logger(__name__)

# Initialize Typer app
app = typer.Typer(
    name="crawl4ai-rag",
    help="Agentic RAG application for crawl4ai",
    add_completion=False
)


class WebsiteType(str, Enum):
    """Website types for scraping."""
    GENERIC = "generic"
    ECOMMERCE = "ecommerce"
    DOCUMENTATION = "documentation"
    BLOG = "blog"


@app.command("analyze")
def analyze(
    url: str = typer.Argument(..., help="URL to analyze"),
    purpose: str = typer.Option("Extract website content", "--purpose", "-p", help="Purpose of the scraping"),
    website_type: Optional[WebsiteType] = typer.Option(None, "--type", "-t", help="Type of website"),
    output_code: bool = typer.Option(True, "--output-code/--no-output-code", help="Output generated code"),
    output_markdown: bool = typer.Option(False, "--output-markdown/--no-output-markdown", help="Output markdown files"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Directory to write markdown files"),
    max_depth: int = typer.Option(1, "--depth", "-d", help="Maximum crawl depth"),
    max_urls: int = typer.Option(10, "--max-urls", "-m", help="Maximum number of URLs to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Analyze a website and generate code and/or markdown.
    """
    # Set up logging
    setup_logging()
    
    # Set log level based on verbose flag
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the analysis
    typer.echo(f"Analyzing {url}...")
    
    try:
        # Run the async function
        result = asyncio.run(_analyze(
            url=url,
            purpose=purpose,
            website_type=website_type.value if website_type else None,
            output_code=output_code,
            output_markdown=output_markdown,
            output_dir=output_dir,
            max_depth=max_depth,
            max_urls=max_urls
        ))
        
        # Print the result
        if result.get("error"):
            typer.echo(f"Error: {result['error']}")
            sys.exit(1)
        
        # Print success message
        typer.echo(f"Analysis completed successfully!")
        
        # Print code if requested
        if output_code and "code" in result:
            typer.echo("\nGenerated Code:")
            typer.echo("=" * 80)
            typer.echo(result["code"])
            typer.echo("=" * 80)
            
            # Save code to file
            code_file = "scraper.py"
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(result["code"])
            typer.echo(f"\nCode saved to {code_file}")
        
        # Print markdown files if requested
        if output_markdown and "markdown_files" in result:
            typer.echo(f"\nGenerated {len(result['markdown_files'])} markdown files:")
            for filename, path in result["markdown_files"].items():
                typer.echo(f"- {path}")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        if verbose:
            import traceback
            typer.echo(traceback.format_exc())
        sys.exit(1)


@app.command("sync")
def sync(
    force: bool = typer.Option(False, "--force", "-f", help="Force update of existing pages"),
    max_concurrent: int = typer.Option(5, "--max-concurrent", "-m", help="Maximum number of concurrent crawls"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Sync crawl4ai GitHub repository and documentation to Supabase.
    """
    # Set up logging
    setup_logging()
    
    # Set log level based on verbose flag
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the sync
    typer.echo("Syncing crawl4ai sources to Supabase...")
    
    try:
        # Run the async function
        result = asyncio.run(_sync(
            force_update=force,
            max_concurrent=max_concurrent
        ))
        
        # Print the result
        if result.get("error"):
            typer.echo(f"Error: {result['error']}")
            sys.exit(1)
        
        # Print success message
        typer.echo(f"Sync completed successfully!")
        typer.echo(f"Processed {result.get('github', 0)} GitHub files")
        typer.echo(f"Processed {result.get('docs', 0)} documentation pages")
        typer.echo(f"Total: {result.get('total', 0)} items")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        if verbose:
            import traceback
            typer.echo(traceback.format_exc())
        sys.exit(1)


@app.command("github")
def github(
    repo: str = typer.Argument(..., help="GitHub repository (owner/repo)"),
    output_dir: str = typer.Option("./output", "--output-dir", "-o", help="Output directory"),
    save_to_supabase: bool = typer.Option(True, "--save-to-supabase/--no-save-to-supabase", help="Save to Supabase"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Scrape GitHub documentation and save to files and/or Supabase.
    """
    # Set up logging
    setup_logging()
    
    # Set log level based on verbose flag
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the GitHub scraper
    typer.echo(f"Scraping GitHub documentation for {repo}...")
    
    try:
        # Construct GitHub URL
        url = f"https://github.com/{repo}"
        
        # Run the async function
        result = asyncio.run(_analyze(
            url=url,
            purpose="Extract GitHub documentation",
            website_type="github",
            output_code=True,
            output_markdown=True,
            output_dir=output_dir
        ))
        
        # Print the result
        if result.get("error"):
            typer.echo(f"Error: {result['error']}")
            sys.exit(1)
        
        # Print success message
        typer.echo(f"GitHub documentation scraping completed successfully!")
        
        # Print markdown files if generated
        if "markdown_files" in result:
            typer.echo(f"\nGenerated {len(result['markdown_files'])} markdown files:")
            for filename, path in result["markdown_files"].items():
                typer.echo(f"- {path}")
        
        # Save to Supabase if requested
        if save_to_supabase:
            typer.echo("\nSaving to Supabase...")
            # Import the necessary modules
            from db_client.repository import PageRepository
            from app.embeddings import generate_embedding
            
            # Run the async function to save to Supabase
            asyncio.run(_save_to_supabase(result, url))
            
            typer.echo("Saved to Supabase successfully!")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        if verbose:
            import traceback
            typer.echo(traceback.format_exc())
        sys.exit(1)


@app.command("detect")
def detect(
    url: str = typer.Argument(..., help="URL to detect type"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Detect the type of a website.
    """
    # Set up logging
    setup_logging()
    
    # Set log level based on verbose flag
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the detection
    typer.echo(f"Detecting type of {url}...")
    
    try:
        # Run the async function
        website_type = asyncio.run(detect_website_type(url))
        
        # Print the result
        typer.echo(f"Detected website type: {website_type}")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        if verbose:
            import traceback
            typer.echo(traceback.format_exc())
        sys.exit(1)


async def _analyze(
    url: str,
    purpose: str,
    website_type: Optional[str] = None,
    output_code: bool = True,
    output_markdown: bool = False,
    output_dir: Optional[str] = None,
    max_depth: int = 1,
    max_urls: int = 10
) -> Dict[str, Any]:
    """
    Analyze a website and generate code and/or markdown.
    
    Args:
        url: The URL to analyze
        purpose: The purpose of the scraping
        website_type: The type of website
        output_code: Whether to output generated code
        output_markdown: Whether to output markdown files
        output_dir: Directory to write markdown files
        max_depth: Maximum crawl depth
        max_urls: Maximum number of URLs to analyze
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Analyze the website
        analysis = await analyze_website(
            url=url,
            website_type=website_type,
            max_depth=max_depth,
            max_urls=max_urls
        )
        
        result = {
            "analysis": analysis,
            "website_type": analysis.get("website_type", "generic")
        }
        
        # Generate code if requested
        if output_code:
            code = await generate_code(
                url=url,
                purpose=purpose,
                website_type=website_type
            )
            result["code"] = code
        
        # Generate markdown if requested
        if output_markdown:
            markdown_files = await export_markdown(
                url=url,
                output_dir=output_dir,
                website_type=website_type,
                max_depth=max_depth,
                max_urls=max_urls
            )
            result["markdown_files"] = markdown_files
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing {url}: {str(e)}")
        return {"error": str(e)}


async def _sync(
    force_update: bool = False,
    max_concurrent: int = 5
) -> Dict[str, int]:
    """
    Sync crawl4ai GitHub repository and documentation to Supabase.
    
    Args:
        force_update: Whether to force update existing pages
        max_concurrent: Maximum number of concurrent crawls
        
    Returns:
        Dictionary with counts of processed documents for each source
    """
    try:
        # Update sources
        return await update_sources(
            force_update=force_update,
            max_concurrent=max_concurrent
        )
    
    except Exception as e:
        logger.error(f"Error syncing sources: {str(e)}")
        return {"error": str(e)}


async def _save_to_supabase(result: Dict[str, Any], url: str) -> bool:
    """
    Save analysis results to Supabase.
    
    Args:
        result: Analysis results
        url: URL of the website
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from datetime import datetime, timezone
        from db_client.repository import PageRepository
        from app.embeddings import generate_embedding
        
        # Create repository
        repo = PageRepository()
        
        # Get analysis
        analysis = result.get("analysis", {})
        
        # Get markdown content
        markdown_files = result.get("markdown_files", {})
        
        # Save each markdown file to Supabase
        for filename, content in markdown_files.items():
            # Generate a URL for the file
            file_url = f"{url}#{filename}"
            
            # Generate a title
            title = f"{filename} - GitHub Documentation"
            
            # Generate a summary
            summary = content[:200] + "..." if len(content) > 200 else content
            
            # Generate metadata
            metadata = {
                "source": "github",
                "filename": filename,
                "url": url,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content)
            }
            
            # Save to Supabase
            await repo.save_page(
                url=file_url,
                content=content,
                title=title,
                summary=summary,
                metadata=metadata
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving to Supabase: {str(e)}")
        return False


if __name__ == "__main__":
    # Set up logging
    setup_logging()
    
    # Run the CLI
    app()
