"""
MCP client utilities for interacting with MCP servers.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import os
import sys
import asyncio
import subprocess
import tempfile

from utils.logging import get_logger
from utils.mcp_subprocess import SubprocessManager

logger = get_logger(__name__)


class McpClient:
    """
    Client for interacting with MCP servers.
    
    Note: This class is being phased out in favor of service-specific
    implementations like GitHubMcpService that use the SubprocessManager.
    It is kept for backward compatibility.
    """
    
    @staticmethod
    async def use_github_mcp(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use a tool from the GitHub MCP server.
        
        Args:
            tool_name: The name of the tool to use
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        try:
            from config import settings
            
            # Use the subprocess-based approach
            logger.info(f"Using subprocess-based GitHub MCP client for tool: {tool_name}")
            
            # Create a subprocess manager for the GitHub MCP server
            manager = SubprocessManager([
                "cmd.exe", "/c", 
                "npx", "-y", "@modelcontextprotocol/server-github"
            ])
            
            # Start the server
            manager.start_server()
            
            try:
                # Send the request
                result = manager.send_request({
                    "server_name": "github.com/modelcontextprotocol/servers/tree/main/src/github",
                    "tool_name": tool_name,
                    "arguments": arguments
                })
                
                return result
            finally:
                # Stop the server
                manager.stop_server()
                
        except Exception as e:
            logger.error(f"Error using GitHub MCP tool {tool_name}: {str(e)}")
            
            # Fall back to mock responses
            logger.warning("Falling back to mock responses")
            if tool_name == "search_repositories":
                return {
                    "items": [
                        {
                            "name": "crawl4ai",
                            "full_name": "unclecode/crawl4ai",
                            "description": "A Python library for web crawling and data extraction",
                            "stargazers_count": 100,
                            "forks_count": 20,
                            "default_branch": "main",
                            "has_issues": True,
                            "has_wiki": True
                        }
                    ]
                }
            elif tool_name == "get_file_contents":
                return {
                    "content": "IyBjcmF3bDRhaQoKQSBQeXRob24gbGlicmFyeSBmb3Igd2ViIGNyYXdsaW5nIGFuZCBkYXRhIGV4dHJhY3Rpb24K",
                    "encoding": "base64",
                    "sha": "abc123"
                }
            else:
                return {"error": f"Mock response not implemented for {tool_name}"}
    
    @staticmethod
    async def use_fetch_mcp(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use a tool from the Fetch MCP server.
        
        Args:
            tool_name: The name of the tool to use
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        try:
            # Use the subprocess-based approach
            logger.info(f"Using subprocess-based Fetch MCP client for tool: {tool_name}")
            
            # Create a subprocess manager for the Fetch MCP server
            manager = SubprocessManager([
                "cmd.exe", "/c", 
                "npx", "-y", "@modelcontextprotocol/server-fetch-mcp"
            ])
            
            # Start the server
            manager.start_server()
            
            try:
                # Send the request
                result = manager.send_request({
                    "server_name": "github.com/zcaceres/fetch-mcp",
                    "tool_name": tool_name,
                    "arguments": arguments
                })
                
                return result
            finally:
                # Stop the server
                manager.stop_server()
                
        except Exception as e:
            logger.error(f"Error using Fetch MCP tool {tool_name}: {str(e)}")
            
            # Return a mock response for testing
            if tool_name == "fetch_html":
                return {
                    "content": "<html><body><h1>Example Page</h1></body></html>"
                }
            elif tool_name == "fetch_markdown":
                return {
                    "content": "# Example Page\n\nThis is an example page."
                }
            else:
                return {"error": f"Mock response not implemented for {tool_name}"}
