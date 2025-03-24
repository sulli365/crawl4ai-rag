"""
GitHub MCP service for interacting with GitHub repositories.
"""

import asyncio
from typing import Dict, List, Any, Optional
import os
import json
from datetime import datetime, timezone
import base64

from utils.logging import get_logger
from utils.mcp_subprocess import SubprocessManager
from db_client.repository import PageRepository
from config import github_config

logger = get_logger(__name__)


class GitHubMcpService:
    """
    Service for interacting with GitHub repositories using MCP subprocess.
    """
    
    def __init__(self):
        """
        Initialize the GitHub MCP service.
        """
        self.manager = SubprocessManager([
            "cmd.exe", "/c", 
            "npx", "-y", "@modelcontextprotocol/server-github"
        ])
        self.manager.start_server()
        self.server_name = "github.com/modelcontextprotocol/servers/tree/main/src/github"
    
    def __del__(self):
        """
        Clean up resources when the service is destroyed.
        """
        if hasattr(self, 'manager'):
            self.manager.stop_server()
    
    async def search_repositories(self, query: str, page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """
        Search for GitHub repositories.
        
        Args:
            query: Search query
            page: Page number
            per_page: Results per page
            
        Returns:
            Search results
        """
        try:
            # Use the subprocess manager to call the GitHub MCP
            result = self.manager.send_request({
                "server_name": self.server_name,
                "tool_name": "search_repositories",
                "arguments": {
                    "query": query,
                    "page": page,
                    "perPage": per_page
                }
            })
            
            # Convert to async for compatibility with existing code
            return result
        except Exception as e:
            logger.error(f"Error searching repositories: {str(e)}")
            return {"error": str(e)}
    
    async def get_file_contents(self, owner: str, repo: str, path: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Get file contents from a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            branch: Branch name
            
        Returns:
            File contents
        """
        try:
            # Prepare parameters
            params = {
                "owner": owner,
                "repo": repo,
                "path": path
            }
            if branch:
                params["branch"] = branch
            
            # Use the subprocess manager to call the GitHub MCP
            result = self.manager.send_request({
                "server_name": self.server_name,
                "tool_name": "get_file_contents",
                "arguments": params
            })
            
            # Convert to async for compatibility with existing code
            return result
        except Exception as e:
            logger.error(f"Error getting file contents: {str(e)}")
            return {"error": str(e)}
    
    async def list_issues(self, owner: str, repo: str, state: str = "all") -> List[Dict[str, Any]]:
        """
        List issues in a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            
        Returns:
            List of issues
        """
        try:
            # Use the subprocess manager to call the GitHub MCP
            result = self.manager.send_request({
                "server_name": self.server_name,
                "tool_name": "list_issues",
                "arguments": {
                    "owner": owner,
                    "repo": repo,
                    "state": state
                }
            })
            
            # Convert to async for compatibility with existing code
            return result
        except Exception as e:
            logger.error(f"Error listing issues: {str(e)}")
            return {"error": str(e)}
    
    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """
        Get details of a specific issue in a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            
        Returns:
            Issue details
        """
        try:
            # Use the subprocess manager to call the GitHub MCP
            result = self.manager.send_request({
                "server_name": self.server_name,
                "tool_name": "get_issue",
                "arguments": {
                    "owner": owner,
                    "repo": repo,
                    "issue_number": issue_number
                }
            })
            
            # Convert to async for compatibility with existing code
            return result
        except Exception as e:
            logger.error(f"Error getting issue: {str(e)}")
            return {"error": str(e)}
    
    async def list_pull_requests(self, owner: str, repo: str, state: str = "all") -> List[Dict[str, Any]]:
        """
        List pull requests in a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Pull request state (open, closed, all)
            
        Returns:
            List of pull requests
        """
        try:
            # Use the subprocess manager to call the GitHub MCP
            result = self.manager.send_request({
                "server_name": self.server_name,
                "tool_name": "list_pull_requests",
                "arguments": {
                    "owner": owner,
                    "repo": repo,
                    "state": state
                }
            })
            
            # Convert to async for compatibility with existing code
            return result
        except Exception as e:
            logger.error(f"Error listing pull requests: {str(e)}")
            return {"error": str(e)}
    
    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """
        Get details of a specific pull request in a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number
            
        Returns:
            Pull request details
        """
        try:
            # Use the subprocess manager to call the GitHub MCP
            result = self.manager.send_request({
                "server_name": self.server_name,
                "tool_name": "get_pull_request",
                "arguments": {
                    "owner": owner,
                    "repo": repo,
                    "pull_number": pull_number
                }
            })
            
            # Convert to async for compatibility with existing code
            return result
        except Exception as e:
            logger.error(f"Error getting pull request: {str(e)}")
            return {"error": str(e)}
