"""
Debug script to inspect the structure of CrawlResult object.

This script provides a controlled view of the CrawlResult object with options
to limit output size and focus on specific aspects of the crawl results.
"""

import asyncio
import argparse
import json
from typing import Optional, List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text to a maximum length with ellipsis."""
    return (text[:max_len] + '...') if len(text) > max_len else text

def format_dict(data: Dict[str, Any], max_depth: int = 2, current_depth: int = 0, max_items: int = 5) -> str:
    """Format dictionary with controlled depth and item count."""
    if current_depth >= max_depth:
        return f"{{{len(data)} items}}"
    
    items = list(data.items())[:max_items]
    formatted_items = []
    
    for k, v in items:
        if isinstance(v, dict):
            value = format_dict(v, max_depth, current_depth + 1, max_items)
        elif isinstance(v, list):
            value = f"[{len(v)} items]"
        elif isinstance(v, str):
            value = f'"{truncate(v, 50)}"'
        else:
            value = str(v)
        formatted_items.append(f'"{k}": {value}')
    
    if len(data) > max_items:
        formatted_items.append(f"... ({len(data) - max_items} more items)")
    
    return "{" + ", ".join(formatted_items) + "}"

async def main():
    """
    Main function to inspect CrawlResult object with controlled output.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Debug CrawlResult structure with controlled output')
    parser.add_argument('--url', type=str, default='https://github.com/unclecode/crawl4ai',
                        help='URL to crawl (default: https://github.com/unclecode/crawl4ai)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Limit number of items shown in lists (default: 10)')
    parser.add_argument('--summary', action='store_true',
                        help='Show only summary information')
    parser.add_argument('--metrics', action='store_true',
                        help='Show detailed metrics')
    parser.add_argument('--links', action='store_true',
                        help='Show extracted links')
    parser.add_argument('--metadata', action='store_true',
                        help='Show metadata')
    parser.add_argument('--no-content', action='store_true',
                        help='Skip content output (html, markdown)')
    parser.add_argument('--output-format', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    
    args = parser.parse_args()
    
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "----disable-dev-shm-usage", "--no-sandbox"],
    )
    
    # Configure crawler
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=['form', 'header'],
        exclude_external_links=True,
        process_iframes=True,
        remove_overlay_elements=True,
    )
    
    print(f"Crawling URL: {args.url}")
    print("This may take a moment...")
    
    # Create the crawler instance
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Crawl the URL
        result = await crawler.arun(
            url=args.url,
            config=crawl_config
        )
        
        # Always show basic summary
        print("\n=== Basic Summary ===")
        print(f"URL: {result.url}")
        print(f"Title: {truncate(getattr(result, 'title', ''))}")
        
        if hasattr(result, 'html'):
            print(f"HTML Content Length: {len(result.html) if result.html else 0} chars")
        if hasattr(result, 'markdown'):
            print(f"Markdown Content Length: {len(result.markdown) if result.markdown else 0} chars")
        
        # Show available attributes if requested
        if not args.summary:
            print("\n=== Available Attributes ===")
            attributes = [attr for attr in dir(result) if not attr.startswith('_') and not callable(getattr(result, attr))]
            print(", ".join(attributes))
        
        # Show detailed metrics if requested
        if args.metrics:
            print("\n=== Detailed Metrics ===")
            if hasattr(result, 'metadata'):
                print(f"Metadata: {format_dict(result.metadata)}")
            
            if hasattr(result, 'stats'):
                print(f"Stats: {format_dict(result.stats)}")
            
            if hasattr(result, 'raw_results'):
                print(f"Raw Results Count: {len(result.raw_results)}")
                
                if result.raw_results and len(result.raw_results) > 0:
                    print(f"\nSample Raw Result (1 of {len(result.raw_results)}):")
                    sample = result.raw_results[0]
                    sample_attrs = [attr for attr in dir(sample) if not attr.startswith('_') and not callable(getattr(sample, attr))]
                    
                    for attr in sample_attrs[:args.limit]:
                        value = getattr(sample, attr)
                        if isinstance(value, str):
                            print(f"  {attr}: {truncate(value, 100)}")
                        elif isinstance(value, (list, tuple)):
                            print(f"  {attr}: [{len(value)} items]")
                        elif isinstance(value, dict):
                            print(f"  {attr}: {format_dict(value)}")
                        else:
                            print(f"  {attr}: {value}")
        
        # Show links if requested
        if args.links and hasattr(result, 'links'):
            print("\n=== Links ===")
            for i, link in enumerate(result.links[:args.limit]):
                print(f"{i+1}. {link}")
            
            if len(result.links) > args.limit:
                print(f"... and {len(result.links) - args.limit} more links")
        
        # Show metadata if requested
        if args.metadata and hasattr(result, 'metadata'):
            print("\n=== Metadata ===")
            print(format_dict(result.metadata, max_depth=3, max_items=args.limit))
        
        # Show content samples unless --no-content is specified
        if not args.no_content:
            if hasattr(result, 'html') and result.html:
                print("\n=== HTML Sample ===")
                print(truncate(result.html, 500))
            
            if hasattr(result, 'markdown') and result.markdown:
                print("\n=== Markdown Sample ===")
                print(truncate(result.markdown, 500))
        
        # Output in JSON format if requested
        if args.output_format == 'json':
            # Create a serializable representation
            output = {
                "url": result.url,
                "title": getattr(result, 'title', ''),
            }
            
            if hasattr(result, 'metadata'):
                output["metadata"] = result.metadata
            
            if args.links and hasattr(result, 'links'):
                output["links"] = result.links[:args.limit]
            
            if not args.no_content:
                if hasattr(result, 'html'):
                    output["html_sample"] = truncate(result.html, 500) if result.html else ""
                if hasattr(result, 'markdown'):
                    output["markdown_sample"] = truncate(result.markdown, 500) if result.markdown else ""
            
            print("\n=== JSON Output ===")
            print(json.dumps(output, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
