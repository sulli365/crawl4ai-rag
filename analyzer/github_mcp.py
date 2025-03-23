"""
GitHub MCP integration for crawl4ai-rag.
"""

from typing import Dict, List, Any, Optional, Tuple
import os
import json
import asyncio
from datetime import datetime, timezone

from utils.logging import get_logger
from utils.mcp_client import McpClient
from db_client.repository import PageRepository
from app.embeddings import generate_embedding

logger = get_logger(__name__)


class GitHubMcpScraper:
    """
    GitHub MCP scraper for retrieving repository content and storing it in Supabase.
    """
    
    def __init__(self, owner: str, repo: str, branch: str = "main"):
        """
        Initialize the GitHub MCP scraper.
        
        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            branch: Branch to sync (default: main)
        """
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.page_repository = PageRepository()
        self.base_url = f"https://github.com/{owner}/{repo}"
        self.processed_count = 0
    
    async def sync_repository(
        self,
        include_issues: bool = False,
        include_pull_requests: bool = False,
        max_chunk_size: int = 4000
    ) -> int:
        """
        Sync GitHub repository content to Supabase using MCP.
        
        Args:
            include_issues: Whether to include issues
            include_pull_requests: Whether to include pull requests
            max_chunk_size: Maximum chunk size for content
            
        Returns:
            Number of pages synced
        """
        try:
            logger.info(f"Syncing repository {self.owner}/{self.repo} (branch: {self.branch})")
            
            # Reset counter
            self.processed_count = 0
            
            # Get repository information
            repo_info = await self._get_repository_info()
            if "error" in repo_info:
                logger.error(f"Error getting repository info: {repo_info['error']}")
                return 0
            
            # Process README first
            await self._process_readme()
            
            # Get file contents
            await self._process_repository_files()
            
            # Process issues if requested
            if include_issues:
                await self._process_issues()
            
            # Process pull requests if requested
            if include_pull_requests:
                await self._process_pull_requests()
            
            logger.info(f"Repository sync completed. Processed {self.processed_count} items.")
            return self.processed_count
            
        except Exception as e:
            logger.error(f"Error syncing repository: {str(e)}")
            return self.processed_count
    
    async def _get_repository_info(self) -> Dict[str, Any]:
        """
        Get repository information using GitHub MCP.
        
        Returns:
            Repository information
        """
        try:
            # Use the GitHub MCP to get repository information
            result = await McpClient.use_github_mcp(
                "search_repositories",
                {
                    "query": f"repo:{self.owner}/{self.repo}"
                }
            )
            
            if "error" in result:
                return result
            
            if not result.get("items"):
                return {"error": f"Repository {self.owner}/{self.repo} not found"}
            
            return result["items"][0]
            
        except Exception as e:
            logger.error(f"Error getting repository info: {str(e)}")
            return {"error": str(e)}
    
    async def _process_readme(self) -> None:
        """
        Process the repository README file.
        """
        try:
            # Use the GitHub MCP to get the README file
            result = await McpClient.use_github_mcp(
                "get_file_contents",
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "path": "README.md",
                    "branch": self.branch
                }
            )
            
            if "error" in result:
                logger.warning(f"README not found: {result.get('error')}")
                return
            
            if not result.get("content"):
                logger.warning("README found but content is empty")
                return
            
            # Decode content if it's base64 encoded
            content = result.get("content", "")
            if result.get("encoding") == "base64":
                import base64
                content = base64.b64decode(content).decode("utf-8")
            
            # Save README to Supabase
            url = f"{self.base_url}/blob/{self.branch}/README.md"
            title = f"README - {self.owner}/{self.repo}"
            
            # Prepare metadata
            metadata = {
                "repo": f"{self.owner}/{self.repo}",
                "owner": self.owner,
                "repo_name": self.repo,
                "branch": self.branch,
                "path": "README.md",
                "type": "file",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content),
                "sha": result.get("sha", "")
            }
            
            # Save to Supabase
            await self.page_repository.save_page(
                url=url,
                content=content,
                title=title,
                metadata=metadata
            )
            
            self.processed_count += 1
            logger.info(f"Processed README for {self.owner}/{self.repo}")
            
        except Exception as e:
            logger.error(f"Error processing README: {str(e)}")
    
    async def _process_repository_files(self) -> None:
        """
        Process repository files recursively.
        """
        try:
            # Start with the root directory
            await self._process_directory("")
            
        except Exception as e:
            logger.error(f"Error processing repository files: {str(e)}")
    
    async def _process_directory(self, path: str) -> None:
        """
        Process a directory and its contents recursively.
        
        Args:
            path: Directory path within the repository
        """
        try:
            # Use the GitHub MCP to get directory contents
            result = await McpClient.use_github_mcp(
                "get_file_contents",
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "path": path,
                    "branch": self.branch
                }
            )
            
            if "error" in result:
                logger.warning(f"Error getting directory contents for {path}: {result.get('error')}")
                return
            
            # If result is a list, it's a directory
            if isinstance(result, list):
                # Process each item in the directory
                for item in result:
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")
                    
                    # Skip .git directory and binary files
                    if item_path.startswith(".git/") or self._is_binary_file(item_path):
                        continue
                    
                    # Process subdirectories recursively
                    if item_type == "dir":
                        await self._process_directory(item_path)
                    
                    # Process files
                    elif item_type == "file":
                        await self._process_file(item_path)
            
            # If result is a dict with content, it's a file
            elif isinstance(result, dict) and "content" in result:
                # This shouldn't happen, but just in case
                await self._process_file(path)
                
        except Exception as e:
            logger.error(f"Error processing directory {path}: {str(e)}")
    
    async def _process_file(self, path: str) -> None:
        """
        Process a file and store its content in Supabase.
        
        Args:
            path: File path within the repository
        """
        try:
            # Skip binary files and non-documentation files
            if self._is_binary_file(path) or not self._is_documentation_file(path):
                return
            
            # Use the GitHub MCP to get file contents
            result = await McpClient.use_github_mcp(
                "get_file_contents",
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "path": path,
                    "branch": self.branch
                }
            )
            
            if "error" in result:
                logger.warning(f"Error getting file contents for {path}: {result.get('error')}")
                return
            
            if not result.get("content"):
                logger.warning(f"File {path} found but content is empty")
                return
            
            # Decode content if it's base64 encoded
            content = result.get("content", "")
            if result.get("encoding") == "base64":
                import base64
                content = base64.b64decode(content).decode("utf-8")
            
            # Save file to Supabase
            url = f"{self.base_url}/blob/{self.branch}/{path}"
            title = f"{os.path.basename(path)} - {self.owner}/{self.repo}"
            
            # Prepare metadata
            metadata = {
                "repo": f"{self.owner}/{self.repo}",
                "owner": self.owner,
                "repo_name": self.repo,
                "branch": self.branch,
                "path": path,
                "type": "file",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content),
                "sha": result.get("sha", ""),
                "file_extension": os.path.splitext(path)[1].lstrip(".")
            }
            
            # Save to Supabase
            await self.page_repository.save_page(
                url=url,
                content=content,
                title=title,
                metadata=metadata
            )
            
            self.processed_count += 1
            logger.info(f"Processed file: {path}")
            
        except Exception as e:
            logger.error(f"Error processing file {path}: {str(e)}")
    
    async def _process_issues(self) -> None:
        """
        Process repository issues.
        """
        try:
            # Use the GitHub MCP to get issues
            result = await McpClient.use_github_mcp(
                "list_issues",
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "state": "all"
                }
            )
            
            if "error" in result:
                logger.warning(f"Error getting issues: {result.get('error')}")
                return
            
            if not result:
                logger.info(f"No issues found for {self.owner}/{self.repo}")
                return
            
            # Process each issue
            for issue in result:
                issue_number = issue.get("number")
                if not issue_number:
                    continue
                
                # Get full issue details
                issue_result = await McpClient.use_github_mcp(
                    "get_issue",
                    {
                        "owner": self.owner,
                        "repo": self.repo,
                        "issue_number": issue_number
                    }
                )
                
                if "error" in issue_result:
                    logger.warning(f"Error getting issue #{issue_number}: {issue_result.get('error')}")
                    continue
                
                # Extract issue content
                title = issue_result.get("title", f"Issue #{issue_number}")
                body = issue_result.get("body", "")
                url = issue_result.get("html_url", f"{self.base_url}/issues/{issue_number}")
                
                # Combine title and body for content
                content = f"# {title}\n\n{body}"
                
                # Prepare metadata
                metadata = {
                    "repo": f"{self.owner}/{self.repo}",
                    "owner": self.owner,
                    "repo_name": self.repo,
                    "type": "issue",
                    "issue_number": issue_number,
                    "state": issue_result.get("state", ""),
                    "created_at": issue_result.get("created_at", ""),
                    "updated_at": issue_result.get("updated_at", ""),
                    "closed_at": issue_result.get("closed_at", ""),
                    "labels": [label.get("name") for label in issue_result.get("labels", [])],
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "content_length": len(content)
                }
                
                # Save to Supabase
                await self.page_repository.save_page(
                    url=url,
                    content=content,
                    title=title,
                    metadata=metadata
                )
                
                self.processed_count += 1
                logger.info(f"Processed issue #{issue_number}")
                
        except Exception as e:
            logger.error(f"Error processing issues: {str(e)}")
    
    async def _process_pull_requests(self) -> None:
        """
        Process repository pull requests.
        """
        try:
            # Use the GitHub MCP to get pull requests
            result = await McpClient.use_github_mcp(
                "list_pull_requests",
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "state": "all"
                }
            )
            
            if "error" in result:
                logger.warning(f"Error getting pull requests: {result.get('error')}")
                return
            
            if not result:
                logger.info(f"No pull requests found for {self.owner}/{self.repo}")
                return
            
            # Process each pull request
            for pr in result:
                pr_number = pr.get("number")
                if not pr_number:
                    continue
                
                # Get full pull request details
                pr_result = await McpClient.use_github_mcp(
                    "get_pull_request",
                    {
                        "owner": self.owner,
                        "repo": self.repo,
                        "pull_number": pr_number
                    }
                )
                
                if "error" in pr_result:
                    logger.warning(f"Error getting PR #{pr_number}: {pr_result.get('error')}")
                    continue
                
                # Extract pull request content
                title = pr_result.get("title", f"Pull Request #{pr_number}")
                body = pr_result.get("body", "")
                url = pr_result.get("html_url", f"{self.base_url}/pull/{pr_number}")
                
                # Combine title and body for content
                content = f"# {title}\n\n{body}"
                
                # Prepare metadata
                metadata = {
                    "repo": f"{self.owner}/{self.repo}",
                    "owner": self.owner,
                    "repo_name": self.repo,
                    "type": "pull_request",
                    "pr_number": pr_number,
                    "state": pr_result.get("state", ""),
                    "created_at": pr_result.get("created_at", ""),
                    "updated_at": pr_result.get("updated_at", ""),
                    "closed_at": pr_result.get("closed_at", ""),
                    "merged_at": pr_result.get("merged_at", ""),
                    "labels": [label.get("name") for label in pr_result.get("labels", [])],
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "content_length": len(content)
                }
                
                # Save to Supabase
                await self.page_repository.save_page(
                    url=url,
                    content=content,
                    title=title,
                    metadata=metadata
                )
                
                self.processed_count += 1
                logger.info(f"Processed pull request #{pr_number}")
                
        except Exception as e:
            logger.error(f"Error processing pull requests: {str(e)}")
    
    def _is_binary_file(self, path: str) -> bool:
        """
        Check if a file is likely binary based on its extension.
        
        Args:
            path: File path
            
        Returns:
            True if the file is likely binary, False otherwise
        """
        binary_extensions = {
            # Images
            "png", "jpg", "jpeg", "gif", "bmp", "ico", "svg", "webp",
            # Audio
            "mp3", "wav", "ogg", "flac", "aac",
            # Video
            "mp4", "webm", "avi", "mov", "wmv", "flv",
            # Archives
            "zip", "tar", "gz", "bz2", "7z", "rar",
            # Executables
            "exe", "dll", "so", "dylib",
            # Other binary formats
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "bin", "dat", "db", "sqlite", "pyc", "pyo", "o", "class"
        }
        
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        return ext in binary_extensions
    
    def _is_documentation_file(self, path: str) -> bool:
        """
        Check if a file is likely documentation based on its name and extension.
        
        Args:
            path: File path
            
        Returns:
            True if the file is likely documentation, False otherwise
        """
        # Documentation file extensions
        doc_extensions = {"md", "rst", "txt", "adoc", "asciidoc", "wiki", "org"}
        
        # Documentation file names
        doc_filenames = {
            "readme", "contributing", "changelog", "changes", "history",
            "license", "licence", "authors", "contributors", "maintainers",
            "hacking", "install", "installation", "setup", "getting_started",
            "getting-started", "guide", "faq", "help", "support", "tutorial",
            "howto", "how-to", "doc", "docs", "documentation"
        }
        
        # Check extension
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        if ext in doc_extensions:
            return True
        
        # Check filename
        filename = os.path.basename(path).lower()
        filename_without_ext = os.path.splitext(filename)[0].lower()
        
        if filename_without_ext in doc_filenames:
            return True
        
        # Check if file is in a docs directory
        path_parts = path.lower().split("/")
        if "docs" in path_parts or "doc" in path_parts or "documentation" in path_parts:
            return True
        
        # Include Python files for API documentation
        if ext == "py" and ("docs" in path_parts or "doc" in path_parts):
            return True
        
        return False


async def sync_github_repository(
    owner: str,
    repo: str,
    branch: str = "main",
    include_issues: bool = False,
    include_pull_requests: bool = False
) -> int:
    """
    Sync GitHub repository content to Supabase using MCP.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        branch: Branch to sync (default: main)
        include_issues: Whether to include issues
        include_pull_requests: Whether to include pull requests
        
    Returns:
        Number of pages synced
    """
    scraper = GitHubMcpScraper(owner, repo, branch)
    return await scraper.sync_repository(include_issues, include_pull_requests)
