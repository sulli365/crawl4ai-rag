# mcp_subprocess.py
import subprocess
import json
import os
import signal
import logging

logger = logging.getLogger(__name__)

class SubprocessManager:
    """
    Manager for one-shot invocation of the MCP server subprocess using stdin/stdout.
    """
    
    def __init__(self, server_cmd: list, timeout: int = 30):
        """
        Args:
            server_cmd (list): Command to start the MCP server,
                e.g. ["npx", "-y", "@modelcontextprotocol/server-github"]
            timeout (int): Timeout in seconds for the subprocess communication.
        """
        self.server_cmd = server_cmd
        self.timeout = timeout

    def send_request_one_shot(self, request: dict) -> dict:
        """
        Starts a new MCP server process, sends a JSON request via stdin,
        and returns the parsed JSON response.
        
        Args:
            request (dict): Request dictionary with keys "tool_name" and "arguments".
            
        Returns:
            dict: Parsed JSON response from the MCP server, or an error dict.
        """
        # Format the request as expected by the MCP protocol (one JSON object per line)
        mcp_request = {
            "tool": request.get("tool_name", ""),
            "args": request.get("arguments", {})
        }
        json_request = json.dumps(mcp_request) + "\n"
        logger.debug(f"Sending one-shot MCP request: {json_request.strip()}")

        try:
            process = subprocess.Popen(
                self.server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            stdout_data, stderr_data = process.communicate(input=json_request, timeout=self.timeout)
            
            if stderr_data:
                logger.warning(f"MCP server stderr: {stderr_data.strip()}")
            if not stdout_data:
                logger.error("No response received from MCP server")
                return {"error": "No response received from MCP server"}
            
            logger.debug(f"Received MCP response: {stdout_data.strip()}")
            try:
                return json.loads(stdout_data.strip())
            except json.JSONDecodeError:
                logger.error(f"Failed to parse MCP response: {stdout_data}")
                return {"error": "Invalid JSON response from MCP server"}
        except subprocess.TimeoutExpired:
            process.kill()
            logger.error(f"Timeout after {self.timeout} seconds waiting for MCP server response")
            return {"error": f"MCP server timed out after {self.timeout} seconds"}
        except Exception as e:
            logger.error(f"Exception during MCP request: {e}")
            return {"error": str(e)}
