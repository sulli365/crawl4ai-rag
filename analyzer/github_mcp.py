# github_mcp.py
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any

from utils.logging import get_logger
from db_client.repository import PageRepository
from app.embeddings import generate_embedding
from config import github_config

logger = get_logger(__name__)

# Define the MCP service inline to avoid extra indirection.
class GitHubMcpService:
    """
    A service that uses the MCP server (via a one-shot subprocess call)
    to perform GitHub-related tasks.
    """
    def __init__(self, timeout: int = 30):
        from mcp_subprocess import SubprocessManager  # local import to avoid circular dependencies
        self.manager = SubprocessManager(["npx", "-y", "@modelcontextprotocol/server-github"], timeout=timeout)
    
    async def search_repositories(self, query: str) -> dict:
        loop = asyncio.get_event_loop()
        request = {"tool_name": "search_repositories", "arguments": {"query": query}}
        return await loop.run_in_executor(None, self.manager.send_request_one_shot, request)
    
    async def get_file_contents(self, owner: str, repo: str, path: str, branch: str = "main") -> dict:
        loop = asyncio.get_event_loop()
        request = {
            "tool_name": "get_file_contents",
            "arguments": {"owner": owner, "repo": repo, "path": path, "branch": branch}
        }
        return await loop.run_in_executor(None, self.manager.send_request_one_shot, request)

    async def list_issues(self, owner: str, repo: str, state: str = "open") -> dict:
        loop = asyncio.get_event_loop()
        request = {
            "tool_name": "list_issues",
            "arguments": {"owner": owner, "repo": repo, "state": state}
        }
        return await loop.run_in_executor(None, self.manager.send_request_one_shot, request)

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        loop = asyncio.get_event_loop()
        request = {
            "tool_name": "get_issue",
            "arguments": {"owner": owner, "repo": repo, "issue_number": issue_number}
        }
        return await loop.run_in_executor(None, self.manager.send_request_one_shot, request)

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> dict:
        loop = asyncio.get_event_loop()
        request = {
            "tool_name": "list_pull_requests",
            "arguments": {"owner": owner, "repo": repo, "state": state}
        }
        return await loop.run_in_executor(None, self.manager.send_request_one_shot, request)

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> dict:
        loop = asyncio.get_event_loop()
        request = {
            "tool_name": "get_pull_request",
            "arguments": {"owner": owner, "repo": repo, "pull_number": pull_number}
        }
        return await loop.run_in_executor(None, self.manager.send_request_one_shot, request)

class GitHubMcpScraper:
    """
    GitHub MCP scraper for retrieving repository content and storing it in Supabase.
    """
    
    def __init__(self, owner: str, repo: str, branch: str = "main"):
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.page_repository = PageRepository()
        self.base_url = f"https://github.com/{owner}/{repo}"
        self.processed_count = 0
        self.github_service = GitHubMcpService()
    
    async def sync_repository(
        self,
        include_issues: bool = False,
        include_pull_requests: bool = False,
        max_chunk_size: int = 4000
    ) -> int:
        try:
            logger.info(f"Syncing repository {self.owner}/{self.repo} (branch: {self.branch})")
            self.processed_count = 0
            repo_info = await self._get_repository_info()
            if "error" in repo_info:
                logger.error(f"Error getting repository info: {repo_info['error']}")
                return 0
            
            await self._process_readme()
            await self._process_repository_files()
            
            if include_issues:
                await self._process_issues()
            if include_pull_requests:
                await self._process_pull_requests()
            
            logger.info(f"Repository sync completed. Processed {self.processed_count} items.")
            return self.processed_count
        except Exception as e:
            logger.error(f"Error syncing repository: {str(e)}")
            return self.processed_count
    
    async def _get_repository_info(self) -> Dict[str, Any]:
        try:
            max_retries = 3
            retry_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    result = await self.github_service.search_repositories(
                        query=f"repo:{self.owner}/{self.repo}"
                    )
                    if "error" in result:
                        logger.warning(f"Error getting repository info: {result.get('error')}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        return result
                    if not result.get("items"):
                        logger.warning(f"Repository {self.owner}/{self.repo} not found")
                        return {"error": f"Repository {self.owner}/{self.repo} not found"}
                    return result["items"][0]
                except Exception as e:
                    logger.error(f"Error getting repository info: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting repository info: {str(e)}")
            return {"error": str(e)}
    
    async def _process_readme(self) -> None:
        try:
            max_retries = 3
            retry_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    result = await self.github_service.get_file_contents(
                        owner=self.owner,
                        repo=self.repo,
                        path="README.md",
                        branch=self.branch
                    )
                    if "error" in result:
                        logger.warning(f"README not found: {result.get('error')}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        return
                    if not result.get("content"):
                        logger.warning("README found but content is empty")
                        return
                    content = result.get("content", "")
                    if result.get("encoding") == "base64":
                        import base64
                        content = base64.b64decode(content).decode("utf-8")
                    url = f"{self.base_url}/blob/{self.branch}/README.md"
                    title = f"README - {self.owner}/{self.repo}"
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
                    await self.page_repository.save_page(url=url, content=content, title=title, metadata=metadata)
                    self.processed_count += 1
                    logger.info(f"Processed README for {self.owner}/{self.repo}")
                    break
                except Exception as e:
                    logger.error(f"Error processing README: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to process README after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Unexpected error processing README: {str(e)}")
    
    async def _process_repository_files(self) -> None:
        try:
            await self._process_directory("")
        except Exception as e:
            logger.error(f"Error processing repository files: {str(e)}")
    
    async def _process_directory(self, path: str) -> None:
        try:
            max_retries = 3
            retry_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    result = await self.github_service.get_file_contents(
                        owner=self.owner,
                        repo=self.repo,
                        path=path,
                        branch=self.branch
                    )
                    if "error" in result:
                        logger.warning(f"Error getting directory contents for {path}: {result.get('error')}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        return
                    if isinstance(result, list):
                        for item in result:
                            item_path = item.get("path", "")
                            item_type = item.get("type", "")
                            if item_path.startswith(".git/") or self._is_binary_file(item_path):
                                continue
                            if any(excl in item_path for excl in github_config.exclude_paths):
                                logger.debug(f"Skipping excluded path: {item_path}")
                                continue
                            if item_type == "dir":
                                await self._process_directory(item_path)
                            elif item_type == "file":
                                await self._process_file(item_path)
                    elif isinstance(result, dict) and "content" in result:
                        await self._process_file(path)
                    break
                except Exception as e:
                    logger.error(f"Error processing directory {path}: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to process directory {path} after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Unexpected error processing directory {path}: {str(e)}")
    
    async def _process_file(self, path: str) -> None:
        try:
            if self._is_binary_file(path):
                return
            include_file = any(re.search(pattern, path) for pattern in github_config.include_patterns)
            if not include_file:
                ext = os.path.splitext(path)[1].lower()
                if ext not in github_config.file_extensions:
                    logger.debug(f"Skipping file with non-matching extension: {path}")
                    return
            max_retries = 3
            retry_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    result = await self.github_service.get_file_contents(
                        owner=self.owner,
                        repo=self.repo,
                        path=path,
                        branch=self.branch
                    )
                    if "error" in result:
                        logger.warning(f"Error getting file contents for {path}: {result.get('error')}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        return
                    if not result.get("content"):
                        logger.warning(f"File {path} found but content is empty")
                        return
                    content = result.get("content", "")
                    if result.get("encoding") == "base64":
                        import base64
                        content = base64.b64decode(content).decode("utf-8")
                    url = f"{self.base_url}/blob/{self.branch}/{path}"
                    title = f"{os.path.basename(path)} - {self.owner}/{self.repo}"
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
                    await self.page_repository.save_page(url=url, content=content, title=title, metadata=metadata)
                    self.processed_count += 1
                    logger.info(f"Processed file: {path}")
                    break
                except Exception as e:
                    logger.error(f"Error processing file {path}: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to process file {path} after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Unexpected error processing file {path}: {str(e)}")
    
    async def _process_issues(self) -> None:
        try:
            max_retries = 3
            retry_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    result = await self.github_service.list_issues(owner=self.owner, repo=self.repo, state="all")
                    if "error" in result:
                        logger.warning(f"Error getting issues: {result.get('error')}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        return
                    if not result:
                        logger.info(f"No issues found for {self.owner}/{self.repo}")
                        return
                    for issue in result:
                        issue_number = issue.get("number")
                        if not issue_number:
                            continue
                        for issue_attempt in range(max_retries):
                            try:
                                issue_result = await self.github_service.get_issue(owner=self.owner, repo=self.repo, issue_number=issue_number)
                                if "error" in issue_result:
                                    logger.warning(f"Error getting issue #{issue_number}: {issue_result.get('error')}")
                                    if issue_attempt < max_retries - 1:
                                        logger.info(f"Retrying issue #{issue_number} ({issue_attempt+1}/{max_retries}) after {retry_delay}s...")
                                        await asyncio.sleep(retry_delay)
                                        continue
                                    break
                                title = issue_result.get("title", f"Issue #{issue_number}")
                                body = issue_result.get("body", "")
                                url = issue_result.get("html_url", f"{self.base_url}/issues/{issue_number}")
                                content = f"# {title}\n\n{body}"
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
                                await self.page_repository.save_page(url=url, content=content, title=title, metadata=metadata)
                                self.processed_count += 1
                                logger.info(f"Processed issue #{issue_number}")
                                break
                            except Exception as e:
                                logger.error(f"Error processing issue #{issue_number}: {str(e)}")
                                if issue_attempt < max_retries - 1:
                                    logger.info(f"Retrying issue #{issue_number} ({issue_attempt+1}/{max_retries}) after {retry_delay}s...")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Failed to process issue #{issue_number} after {max_retries} attempts")
                    break
                except Exception as e:
                    logger.error(f"Error processing issues: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying issues list ({attempt+1}/{max_retries}) after {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to process issues after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Unexpected error processing issues: {str(e)}")
    
    async def _process_pull_requests(self) -> None:
        try:
            max_retries = 3
            retry_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    result = await self.github_service.list_pull_requests(owner=self.owner, repo=self.repo, state="all")
                    if "error" in result:
                        logger.warning(f"Error getting pull requests: {result.get('error')}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying ({attempt+1}/{max_retries}) after {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        return
                    if not result:
                        logger.info(f"No pull requests found for {self.owner}/{self.repo}")
                        return
                    for pr in result:
                        pr_number = pr.get("number")
                        if not pr_number:
                            continue
                        for pr_attempt in range(max_retries):
                            try:
                                pr_result = await self.github_service.get_pull_request(owner=self.owner, repo=self.repo, pull_number=pr_number)
                                if "error" in pr_result:
                                    logger.warning(f"Error getting PR #{pr_number}: {pr_result.get('error')}")
                                    if pr_attempt < max_retries - 1:
                                        logger.info(f"Retrying PR #{pr_number} ({pr_attempt+1}/{max_retries}) after {retry_delay}s...")
                                        await asyncio.sleep(retry_delay)
                                        continue
                                    break
                                title = pr_result.get("title", f"Pull Request #{pr_number}")
                                body = pr_result.get("body", "")
                                url = pr_result.get("html_url", f"{self.base_url}/pull/{pr_number}")
                                content = f"# {title}\n\n{body}"
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
                                await self.page_repository.save_page(url=url, content=content, title=title, metadata=metadata)
                                self.processed_count += 1
                                logger.info(f"Processed pull request #{pr_number}")
                                break
                            except Exception as e:
                                logger.error(f"Error processing PR #{pr_number}: {str(e)}")
                                if pr_attempt < max_retries - 1:
                                    logger.info(f"Retrying PR #{pr_number} ({pr_attempt+1}/{max_retries}) after {retry_delay}s...")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Failed to process PR #{pr_number} after {max_retries} attempts")
                    break
                except Exception as e:
                    logger.error(f"Error processing pull requests: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying pull requests list ({attempt+1}/{max_retries}) after {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to process pull requests after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Unexpected error processing pull requests: {str(e)}")
    
    def _is_binary_file(self, path: str) -> bool:
        binary_extensions = {
            "png", "jpg", "jpeg", "gif", "bmp", "ico", "svg", "webp",
            "mp3", "wav", "ogg", "flac", "aac",
            "mp4", "webm", "avi", "mov", "wmv", "flv",
            "zip", "tar", "gz", "bz2", "7z", "rar",
            "exe", "dll", "so", "dylib",
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "bin", "dat", "db", "sqlite", "pyc", "pyo", "o", "class"
        }
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        return ext in binary_extensions

    def _is_documentation_file(self, path: str) -> bool:
        doc_extensions = {"md", "rst", "txt", "adoc", "asciidoc", "wiki", "org"}
        doc_filenames = {
            "readme", "contributing", "changelog", "changes", "history",
            "license", "licence", "authors", "contributors", "maintainers",
            "hacking", "install", "installation", "setup", "getting_started",
            "getting-started", "guide", "faq", "help", "support", "tutorial",
            "howto", "how-to", "doc", "docs", "documentation"
        }
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        if ext in doc_extensions:
            return True
        filename = os.path.basename(path).lower()
        filename_without_ext = os.path.splitext(filename)[0].lower()
        if filename_without_ext in doc_filenames:
            return True
        path_parts = path.lower().split("/")
        if "docs" in path_parts or "doc" in path_parts or "documentation" in path_parts:
            return True
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
    scraper = GitHubMcpScraper(owner, repo, branch)
    return await scraper.sync_repository(include_issues, include_pull_requests)