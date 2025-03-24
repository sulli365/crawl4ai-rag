# test_github_mcp.py
import asyncio
import sys
from datetime import datetime

from github_mcp import sync_github_repository
from utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# Set a timeout for the repository sync (in seconds)
SYNC_TIMEOUT = 60

class ProgressIndicator:
    """Simple progress indicator for console output."""
    
    def __init__(self, message="Processing"):
        self.message = message
        self.running = False
        self.task = None
        
    async def _show_progress(self):
        """Show a spinning progress indicator."""
        spinner = "|/-\\"
        i = 0
        while self.running:
            sys.stdout.write(f"\r{self.message} {spinner[i % len(spinner)]} ")
            sys.stdout.flush()
            i += 1
            await asyncio.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()
    
    def start(self):
        """Start the progress indicator."""
        self.running = True
        self.task = asyncio.create_task(self._show_progress())
        
    def stop(self):
        """Stop the progress indicator."""
        self.running = False
        if self.task:
            self.task.cancel()

async def test_github_mcp():
    """
    Test GitHub MCP integration with the crawl4ai repository.
    """
    owner = "unclecode"
    repo = "crawl4ai"
    
    print(f"Testing GitHub MCP integration with {owner}/{repo}")
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Timeout set to {SYNC_TIMEOUT} seconds")
    print("=" * 50)
    
    progress = ProgressIndicator(f"Syncing repository {owner}/{repo}")
    
    try:
        progress.start()
        sync_task = asyncio.create_task(
            sync_github_repository(
                owner=owner,
                repo=repo,
                branch="main",
                include_issues=False,
                include_pull_requests=False
            )
        )
        try:
            count = await asyncio.wait_for(sync_task, timeout=SYNC_TIMEOUT)
            print(f"\nSynced {count} items from GitHub repository {owner}/{repo} to Supabase")
            print(f"Completed at: {datetime.now().strftime('%H:%M:%S')}")
        except asyncio.TimeoutError:
            print(f"\nTimeout after {SYNC_TIMEOUT} seconds. The operation may still be running in the background.")
            print("Check the logs for more information.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        logger.error(f"Error syncing repository: {str(e)}")
    finally:
        progress.stop()
        print("=" * 50)

if __name__ == "__main__":
    try:
        asyncio.run(test_github_mcp())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
