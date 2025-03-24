"""
MCP subprocess utilities for interacting with MCP servers via stdin/stdout.
"""

import subprocess
import json
from typing import Dict, Any, Optional, List

from utils.logging import get_logger

logger = get_logger(__name__)


class SubprocessManager:
    """
    Manager for MCP server subprocesses with stdin/stdout communication.
    """
    
    def __init__(self, server_cmd: List[str]):
        """
        Initialize the subprocess manager.
        
        Args:
            server_cmd: Command to start the MCP server
        """
        self.server_cmd = server_cmd
        self.process = None
        
    def start_server(self):
        """
        Start the MCP server subprocess.
        """
        logger.info(f"Starting MCP server: {' '.join(self.server_cmd)}")
        self.process = subprocess.Popen(
            self.server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON request and get response.
        
        Args:
            request: Request to send to the MCP server
            
        Returns:
            Response from the MCP server
        """
        if not self.process:
            logger.error("Server not started")
            raise RuntimeError("Server not started")
            
        try:
            # Send request
            json_request = json.dumps(request) + "\n"
            self.process.stdin.write(json_request)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            
            # Check for stderr output
            stderr_data = ""
            while self.process.stderr.readable() and self.process.poll() is None:
                line = self.process.stderr.readline()
                if not line:
                    break
                stderr_data += line
            
            if stderr_data:
                logger.warning(f"MCP stderr: {stderr_data}")
            
            # Parse the response
            try:
                return json.loads(response_line)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse response: {response_line}")
                return {"error": "Invalid JSON response"}
                
        except Exception as e:
            logger.error(f"Error sending request to MCP server: {str(e)}")
            return {"error": str(e)}
        
    def stop_server(self):
        """
        Terminate the server process.
        """
        if self.process:
            logger.info("Stopping MCP server")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("MCP server did not terminate gracefully, killing")
                self.process.kill()
