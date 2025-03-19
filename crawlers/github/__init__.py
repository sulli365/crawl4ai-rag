"""
GitHub crawler for the crawl4ai repository.
"""

import os
import asyncio
import base64
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin

import httpx
from loguru import logger

from ...config import settings
from ...utils.logging import get_logger
from ...supabase.repository import PageRepository

logger = get_logger(__name__)


class GitHubCrawler:
    """
    Crawler for the crawl4ai GitHub repository.
    """
    
    def __init__(self, repo: str = None, token: Optional[str] = None):
        """
        Initialize the GitHub crawler.
        
        Args:
            repo: The repository to crawl (owner/repo)
            token: GitHub API token for authentication
        """
        self.repo = repo or settings.github_repo
        self.token = token or settings.github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        
        # Add token if available
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        
        self.page_repo = PageRepository()
    
    async def _make_request(self, url: str) -> Dict[str, Any]:
        """
        Make a request to the GitHub API.
        
        Args:
            url: The URL to request
            
        Returns:
            The response data
        """
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    async def get_file_content(self, path: str, ref: str = "main") -> Tuple[str, Dict[str, Any]]:
        """
        Get the content of a file from the repository.
        
        Args:
            path: The path to the file
            ref: The branch or commit reference
            
        Returns:
            Tuple of (content, metadata)
        """
        url = f"{self.base_url}/repos/{self.repo}/contents/{path}?ref={ref}"
        
        try:
            data = await self._make_request(url)
            
            if data.get("type") != "file":
                raise ValueError(f"Path is not a file: {path}")
            
            # Decode content
            content = base64.b64decode(data["content"]).decode("utf-8")
            
            # Extract metadata
            metadata = {
                "sha": data.get("sha", ""),
                "size": data.get("size", 0),
                "path": data.get("path", ""),
                "url": data.get("html_url", ""),
                "source": "github",
                "repo": self.repo,
                "ref": ref
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Error getting file content for {path}: {str(e)}")
            return "", {}
    
    async def get_directory_contents(self, path: str = "", ref: str = "main") -> List[Dict[str, Any]]:
        """
        Get the contents of a directory from the repository.
        
        Args:
            path: The path to the directory
            ref: The branch or commit reference
            
        Returns:
            List of file/directory information
        """
        url = f"{self.base_url}/repos/{self.repo}/contents/{path}?ref={ref}"
        
        try:
            return await self._make_request(url)
        except Exception as e:
            logger.error(f"Error getting directory contents for {path}: {str(e)}")
            return []
    
    async def crawl_directory(self, path: str = "", ref: str = "main", max_depth: int = 3) -> List[str]:
        """
        Recursively crawl a directory and its subdirectories.
        
        Args:
            path: The path to the directory
            ref: The branch or commit reference
            max_depth: Maximum recursion depth
            
        Returns:
            List of file paths
        """
        if max_depth <= 0:
            return []
        
        file_paths = []
        contents = await self.get_directory_contents(path, ref)
        
        for item in contents:
            item_path = item.get("path", "")
            item_type = item.get("type", "")
            
            if item_type == "file":
                # Skip non-text files
                name = item.get("name", "")
                if not self._is_text_file(name):
                    continue
                
                file_paths.append(item_path)
            
            elif item_type == "dir" and max_depth > 1:
                # Recursively crawl subdirectory
                sub_paths = await self.crawl_directory(item_path, ref, max_depth - 1)
                file_paths.extend(sub_paths)
        
        return file_paths
    
    def _is_text_file(self, filename: str) -> bool:
        """
        Check if a file is likely to be a text file based on its extension.
        
        Args:
            filename: The filename to check
            
        Returns:
            True if the file is likely to be a text file, False otherwise
        """
        text_extensions = {
            ".py", ".md", ".txt", ".rst", ".json", ".yml", ".yaml", 
            ".toml", ".ini", ".cfg", ".html", ".css", ".js", ".ts",
            ".jsx", ".tsx", ".xml", ".csv", ".sh", ".bat", ".ps1"
        }
        
        _, ext = os.path.splitext(filename.lower())
        return ext in text_extensions
    
    async def process_file(self, path: str, ref: str = "main") -> bool:
        """
        Process a file and save it to the database.
        
        Args:
            path: The path to the file
            ref: The branch or commit reference
            
        Returns:
            True if successful, False otherwise
        """
        try:
            content, metadata = await self.get_file_content(path, ref)
            
            if not content:
                logger.warning(f"Empty content for file: {path}")
                return False
            
            # Create URL for the file
            url = f"https://github.com/{self.repo}/blob/{ref}/{path}"
            
            # Generate title from path
            filename = os.path.basename(path)
            title = f"{filename} - {self.repo} GitHub"
            
            # Generate summary (first 100 characters)
            summary = content[:100] + "..." if len(content) > 100 else content
            
            # Save to database
            await self.page_repo.save_page(
                url=url,
                content=content,
                title=title,
                summary=summary,
                metadata=metadata
            )
            
            logger.info(f"Processed file: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {path}: {str(e)}")
            return False
    
    async def crawl_repository(self, ref: str = "main", max_depth: int = 3) -> int:
        """
        Crawl the entire repository and save files to the database.
        
        Args:
            ref: The branch or commit reference
            max_depth: Maximum recursion depth
            
        Returns:
            Number of files processed
        """
        logger.info(f"Starting crawl of repository: {self.repo}")
        
        try:
            # Get all file paths
            file_paths = await self.crawl_directory("", ref, max_depth)
            
            # Process files in parallel with concurrency limit
            semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
            
            async def process_with_semaphore(path: str) -> bool:
                async with semaphore:
                    return await self.process_file(path, ref)
            
            # Process all files
            results = await asyncio.gather(
                *[process_with_semaphore(path) for path in file_paths]
            )
            
            # Count successful processes
            processed_count = sum(1 for result in results if result)
            
            logger.info(f"Completed crawl of repository: {self.repo}. Processed {processed_count} files.")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error crawling repository {self.repo}: {str(e)}")
            return 0


async def crawl_github_repository(
    repo: str = None, 
    token: Optional[str] = None,
    ref: str = "main",
    max_depth: int = 3
) -> int:
    """
    Crawl a GitHub repository and save files to the database.
    
    Args:
        repo: The repository to crawl (owner/repo)
        token: GitHub API token for authentication
        ref: The branch or commit reference
        max_depth: Maximum recursion depth
        
    Returns:
        Number of files processed
    """
    crawler = GitHubCrawler(repo, token)
    return await crawler.crawl_repository(ref, max_depth)
