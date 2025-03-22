"""
Test script for the GitHub documentation scraper.
"""

import asyncio
import os
import sys
from cli import github as github_command

async def test_github_scraper():
    """Test the GitHub documentation scraper with the crawl4ai repository."""
    # Set up test parameters
    repo = "unclecode/crawl4ai"  # The crawl4ai repository
    output_dir = "./output/github_test"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the GitHub scraper command
    print(f"Testing GitHub scraper with repository: {repo}")
    
    try:
        # Import the necessary functions from cli module
        from cli import _analyze, _save_to_supabase
        
        # Run the analyze function
        url = f"https://github.com/{repo}"
        result = await _analyze(
            url=url,
            purpose="Extract GitHub documentation",
            website_type="github",
            output_code=True,
            output_markdown=True,
            output_dir=output_dir
        )
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        print(f"GitHub documentation scraping completed successfully!")
        
        # Print markdown files if generated
        if "markdown_files" in result:
            print(f"\nGenerated {len(result['markdown_files'])} markdown files:")
            for filename, path in result["markdown_files"].items():
                print(f"- {path}")
        
        # Save to Supabase
        print("\nSaving to Supabase...")
        await _save_to_supabase(result, url)
        
        # Verify data in Supabase
        print("\nVerifying data in Supabase...")
        from db_client.repository import PageRepository
        repo = PageRepository()
        urls = await repo.get_all_urls()
        github_urls = [url for url in urls if "github.com/unclecode/crawl4ai" in url]
        print(f"Found {len(github_urls)} crawl4ai GitHub pages in Supabase:")
        for url in github_urls[:5]:  # Show first 5 URLs
            print(f"- {url}")
        
        print("\nTest completed!")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_github_scraper())
