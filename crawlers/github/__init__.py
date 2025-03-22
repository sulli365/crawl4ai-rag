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

from config import settings
from utils.logging import get_logger
from db_client.repository import PageRepository

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
        doc_file_paths = []  # Separate list for documentation files
        contents = await self.get_directory_contents(path, ref)
        
        for item in contents:
            item_path = item.get("path", "")
            item_type = item.get("type", "")
            
            if item_type == "file":
                # Skip non-text files
                name = item.get("name", "")
                if not self._is_text_file(name):
                    continue
                
                # Check if it's a documentation file
                if self._is_documentation_file(name):
                    doc_file_paths.append(item_path)
                else:
                    file_paths.append(item_path)
            
            elif item_type == "dir" and max_depth > 1:
                # Prioritize directories that might contain documentation
                dir_name = os.path.basename(item_path).lower()
                if any(doc_dir in dir_name for doc_dir in ["docs", "documentation", "wiki", "guide"]):
                    # Increase depth for documentation directories
                    sub_paths = await self.crawl_directory(item_path, ref, max_depth)
                else:
                    # Recursively crawl subdirectory
                    sub_paths = await self.crawl_directory(item_path, ref, max_depth - 1)
                
                file_paths.extend(sub_paths)
        
        # Prioritize documentation files by returning them first
        return doc_file_paths + file_paths
    
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
    
    def _is_documentation_file(self, filename: str) -> bool:
        """
        Check if a file is likely to be a documentation file based on its name and extension.
        
        Args:
            filename: The filename to check
            
        Returns:
            True if the file is likely to be a documentation file, False otherwise
        """
        # Documentation file extensions
        doc_extensions = {".md", ".rst", ".txt", ".html"}
        
        # Documentation file patterns
        doc_patterns = [
            "readme", "documentation", "docs", "guide", "tutorial",
            "manual", "reference", "api", "howto", "faq", "wiki"
        ]
        
        # Check extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in doc_extensions:
            return False
        
        # Check filename patterns
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in doc_patterns)
    
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
            
            # Check if this is a documentation file
            is_doc = self._is_documentation_file(filename)
            
            # Add documentation-specific metadata
            if is_doc:
                metadata["is_documentation"] = True
                metadata["doc_type"] = self._determine_doc_type(filename, content)
                
                # Extract documentation metrics if it's a documentation file
                doc_metrics = self._extract_doc_metrics(content)
                if doc_metrics:
                    metadata["doc_metrics"] = doc_metrics
            
            # Save to database
            await self.page_repo.save_page(
                url=url,
                content=content,
                title=title,
                summary=summary,
                metadata=metadata
            )
            
            logger.info(f"Processed file: {path} {'(documentation)' if is_doc else ''}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {path}: {str(e)}")
            return False
    
    def _determine_doc_type(self, filename: str, content: str) -> str:
        """
        Determine the type of documentation file.
        
        Args:
            filename: The filename
            content: The file content
            
        Returns:
            Documentation type
        """
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        if "readme" in filename_lower:
            return "readme"
        elif "api" in filename_lower or "reference" in filename_lower:
            return "api"
        elif "tutorial" in filename_lower or "guide" in filename_lower:
            return "tutorial"
        elif "faq" in filename_lower:
            return "faq"
        
        # Check content for indicators
        if "# api" in content_lower or "## api" in content_lower:
            return "api"
        elif "# tutorial" in content_lower or "## tutorial" in content_lower:
            return "tutorial"
        elif "# guide" in content_lower or "## guide" in content_lower:
            return "guide"
        elif "# faq" in content_lower or "## faq" in content_lower:
            return "faq"
        
        return "general"
    
    def _extract_doc_metrics(self, content: str) -> Dict[str, Any]:
        """
        Extract basic documentation metrics from content.
        
        Args:
            content: The file content
            
        Returns:
            Dictionary with documentation metrics
        """
        lines = content.split("\n")
        
        # Count headings by level
        headings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        for line in lines:
            if line.startswith("#"):
                level = 0
                for char in line:
                    if char == "#":
                        level += 1
                    else:
                        break
                if 1 <= level <= 6:
                    headings[level] += 1
        
        # Count code blocks
        code_blocks = content.count("```")
        code_blocks = code_blocks // 2  # Each block has opening and closing ```
        
        # Count links
        link_count = content.count("](")
        
        # Estimate reading time (average reading speed: 200 words per minute)
        word_count = len(content.split())
        reading_time_minutes = max(1, round(word_count / 200))
        
        return {
            "headings": headings,
            "total_headings": sum(headings.values()),
            "code_blocks": code_blocks,
            "link_count": link_count,
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes
        }
    
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
