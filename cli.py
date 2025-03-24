#!/usr/bin/env python3
"""
Command-line interface for crawl4ai-rag.
"""

import asyncio
import os
import sys
from typing import List, Optional

import typer
from loguru import logger

from analyzer.github_mcp import sync_github_repository
from utils.logging import setup_logging

app = typer.Typer(help="crawl4ai-rag: Analyze websites and generate code/markdown")
setup_logging()


@app.command()
def analyze(
    url: str = typer.Option(..., "--url", "-u", help="URL to analyze"),
    purpose: str = typer.Option("Extract documentation", "--purpose", "-p", help="Purpose of scraping"),
    output_code: bool = typer.Option(True, "--output-code", "-c", help="Output generated code"),
    output_markdown: bool = typer.Option(False, "--output-markdown", "-m", help="Output markdown"),
    output_dir: str = typer.Option("./output", "--output-dir", "-o", help="Output directory for markdown"),
    use_mcp: bool = typer.Option(True, "--use-mcp", help="Use MCP for enhanced capabilities")
):
    """
    Analyze a website and generate code/markdown based on purpose.
    """
    from app.main import analyze_and_generate
    
    try:
        result = asyncio.run(analyze_and_generate(
            urls=[url],
            purpose=purpose,
            output_code=output_code,
            output_markdown=output_markdown,
            markdown_output_dir=output_dir,
            use_mcp=use_mcp
        ))
        
        if "error" in result:
            logger.error(f"Error: {result['error']}")
            sys.exit(1)
        
        if output_code and "code" in result:
            print("\n=== Generated Code ===\n")
            print(result["code"])
        
        if output_markdown and "markdown_files" in result:
            print("\n=== Generated Markdown Files ===\n")
            for file in result["markdown_files"]:
                print(f"- {file}")
        
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


@app.command()
def sync(
    url: str = typer.Option(..., "--url", "-u", help="URL to sync"),
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum crawl depth"),
    force: bool = typer.Option(False, "--force", "-f", help="Force update existing pages"),
    use_mcp: bool = typer.Option(True, "--use-mcp", help="Use MCP for enhanced capabilities")
):
    """
    Sync a website to Supabase.
    """
    from app.main import sync_website_to_supabase
    
    try:
        count = asyncio.run(sync_website_to_supabase(
            url=url,
            max_depth=depth,
            force_update=force,
            use_mcp=use_mcp
        ))
        
        logger.info(f"Synced {count} pages to Supabase")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


@app.command()
def sync_github(
    owner: str = typer.Option(None, "--owner", "-o", help="Repository owner (username or organization)"),
    repo: str = typer.Option(None, "--repo", "-r", help="Repository name"),
    repos: List[str] = typer.Option(None, "--repos", help="GitHub repos in owner/repo format. Overrides config defaults"),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch to sync"),
    include_issues: bool = typer.Option(False, "--include-issues", "-i", help="Include issues"),
    include_pull_requests: bool = typer.Option(False, "--include-prs", "-p", help="Include pull requests")
):
    """
    Sync GitHub repository content to Supabase using MCP.
    """
    from config import github_config
    
    try:
        # Determine which repositories to sync
        repositories_to_sync = []
        
        # If repos option is provided, use those
        if repos:
            repositories_to_sync = repos
        # If owner and repo are provided, use those
        elif owner and repo:
            repositories_to_sync = [f"{owner}/{repo}"]
        # Otherwise, use the configured target_repos
        else:
            repositories_to_sync = github_config.target_repos
            
        if not repositories_to_sync:
            logger.error("No repositories specified. Use --repos, --owner/--repo, or configure target_repos in settings.")
            sys.exit(1)
            
        total_count = 0
        for repo_string in repositories_to_sync:
            try:
                # Parse owner/repo format
                parts = repo_string.split('/')
                if len(parts) != 2:
                    logger.error(f"Invalid repository format: {repo_string}. Expected format: owner/repo")
                    continue
                    
                owner, repo = parts
                
                logger.info(f"Syncing repository: {owner}/{repo}")
                count = asyncio.run(sync_github_repository(
                    owner=owner,
                    repo=repo,
                    branch=branch,
                    include_issues=include_issues,
                    include_pull_requests=include_pull_requests
                ))
                
                logger.info(f"Synced {count} items from GitHub repository {owner}/{repo} to Supabase")
                total_count += count
                
            except Exception as e:
                logger.error(f"Error syncing repository {repo_string}: {str(e)}")
                
        logger.info(f"Total items synced: {total_count}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    app()
