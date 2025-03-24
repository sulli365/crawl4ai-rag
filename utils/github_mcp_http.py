"""
HTTP-based client for the GitHub MCP server.
"""

import subprocess
import requests
import time
import json
import asyncio
import os
from typing import Dict, Any, Optional

from utils.logging import get_logger

logger = get_logger(__name__)

class GithubMcpHttpClient:
    """
    HTTP-based client for the GitHub MCP server.
    """
    
    @staticmethod
    async def wait_for_server_ready(url: str, timeout: int = 10, interval: float = 0.5) -> bool:
        """
        Polls the given URL until the server responds or timeout is reached.
        
        Args:
            url: URL to poll
            timeout: Maximum time to wait in seconds
            interval: Time between polling attempts in seconds
            
        Returns:
            True if server becomes ready, False otherwise
        """
        logger.info(f"Waiting for server to respond at {url}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(url)
                if r.status_code < 500:
                    logger.info("Server is ready.")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            await asyncio.sleep(interval)
        logger.error("Server did not become ready in time.")
        return False
    
    @staticmethod
    async def run_github_mcp_and_request(
        tool_name: str,
        arguments: Dict[str, Any],
        github_token: str,
        server_url: str = "http://localhost:3000",
        request_timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Starts the GitHub MCP server, sends a request, and returns the response.
        
        Args:
            tool_name: Name of the GitHub MCP tool to use
            arguments: Arguments to pass to the tool
            github_token: GitHub personal access token
            server_url: URL where the server will be running
            request_timeout: Timeout for the request in seconds
            
        Returns:
            Response from the GitHub MCP server
        """
        try:
            logger.info(f"Starting GitHub MCP server for tool: {tool_name}")
            
            # Create environment variables for the subprocess
            env = os.environ.copy()
            env["GITHUB_TOKEN"] = github_token
            
            # Run the GitHub MCP server using npx
            proc = subprocess.Popen(
                ["cmd.exe", "/c", "npx", "-y", "@modelcontextprotocol/server-github"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the server to be ready
            if not await GithubMcpHttpClient.wait_for_server_ready(server_url, timeout=15):
                proc.kill()
                return {"error": "MCP server did not become ready."}
            
            # Prepare the request payload
            payload = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "callTool",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send the request to the server
            logger.info(f"Sending request to MCP server: {tool_name}")
            response = requests.post(
                server_url,
                json=payload,
                timeout=request_timeout
            )
            
            # Parse the response
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "result" in result:
                        logger.info(f"Successfully received response for {tool_name}")
                        return result["result"]
                    elif "error" in result:
                        logger.error(f"Error from MCP server: {result['error']}")
                        return {"error": result["error"]}
                    else:
                        logger.error(f"Invalid response format: {result}")
                        return {"error": "Invalid response format"}
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse response: {response.text}")
                    return {"error": "Invalid JSON response"}
            else:
                logger.error(f"HTTP error: {response.status_code} - {response.text}")
                return {"error": f"HTTP error: {response.status_code}"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {str(e)}")
            return {"error": f"HTTP request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
        finally:
            # Always clean up the process
            if 'proc' in locals():
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    proc.kill()
