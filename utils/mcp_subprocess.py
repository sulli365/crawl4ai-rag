"""
MCP subprocess utilities for interacting with MCP servers via stdin/stdout.
"""

import subprocess
import json
import time
import os
import signal
import threading
from typing import Dict, Any, Optional, List, Tuple

from utils.logging import get_logger

logger = get_logger(__name__)


class SubprocessManager:
    """
    Manager for MCP server subprocesses with stdin/stdout communication.
    """
    
    def __init__(self, server_cmd: List[str], timeout: int = 30):
        """
        Initialize the subprocess manager.
        
        Args:
            server_cmd: Command to start the MCP server
            timeout: Timeout in seconds for subprocess communication
        """
        self.server_cmd = server_cmd
        self.process = None
        self.timeout = timeout
        
    def start_server(self):
        """
        Start the MCP server subprocess.
        """
        logger.info(f"Starting MCP server: {' '.join(self.server_cmd)}")
        
        # Create environment variables for the subprocess
        env = os.environ.copy()
        
        # Start the process
        try:
            self.process = subprocess.Popen(
                self.server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Wait a moment for the server to start
            time.sleep(1)
            
            # Check if the process is still running
            if self.process.poll() is not None:
                logger.error(f"MCP server process exited with code {self.process.returncode}")
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    logger.error(f"MCP server stderr: {stderr_output}")
                raise RuntimeError(f"MCP server process exited with code {self.process.returncode}")
                
            logger.info("MCP server started successfully")
            
        except Exception as e:
            logger.error(f"Error starting MCP server: {str(e)}")
            raise
        
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON request and get response.
        
        Args:
            request: Request to send to the MCP server
            
        Returns:
            Response from the MCP server
        """
        # Use the running MCP server process
        if not self.process.stdin or not self.process.stdout:
            logger.error("MCP server stdin/stdout not available")
            return {"error": "MCP server communication channel is broken"}

        mcp_request = {
            "tool": request.get("tool_name", ""),
            "args": request.get("arguments", {})
        }

        json_request = json.dumps(mcp_request) + "\n"

        try:
            # Send the request
            self.process.stdin.write(json_request)
            self.process.stdin.flush()

            # Read the response line (the server sends a single line JSON response)
            stdout_line, stderr_data = self._read_with_timeout()

            if stderr_data:
                logger.warning(f"MCP server stderr: {stderr_data}")
            if not stdout_line:
                logger.error("No response received from MCP server")
                return {"error": "No response received from MCP server"}

            try:
                logger.debug(f"Received response: {stdout_line.strip()}")
                return json.loads(stdout_line.strip())
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from MCP server: {stdout_line}")
                return {"error": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Exception during request: {e}")
            return {"error": str(e)}

    
    def _read_with_timeout(self) -> Tuple[str, str]:
        """
        Read from stdout and stderr with a timeout.
        
        Returns:
            Tuple of (stdout_line, stderr_data)
        """
        stdout_line = ""
        stderr_data = ""
        
        # Define reader functions
        def read_stdout():
            nonlocal stdout_line
            stdout_line = self.process.stdout.readline()
            
        def read_stderr():
            nonlocal stderr_data
            while self.process.stderr.readable() and self.process.poll() is None:
                line = self.process.stderr.readline()
                if not line:
                    break
                stderr_data += line
        
        # Create and start reader threads
        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for stdout thread to complete with timeout
        stdout_thread.join(self.timeout)
        
        # If stdout thread is still alive after timeout, it's hanging
        if stdout_thread.is_alive():
            logger.error(f"Timeout after {self.timeout} seconds waiting for MCP server response")
            return "", stderr_data
        
        # Wait a bit for stderr thread to complete
        stderr_thread.join(1)
        
        return stdout_line, stderr_data
        
    def stop_server(self):
        """
        Terminate the server process.
        """
        if self.process:
            logger.info("Stopping MCP server")
            
            try:
                # Try to terminate gracefully first
                if os.name == 'nt':  # Windows
                    self.process.terminate()
                else:  # Unix/Linux/Mac
                    os.kill(self.process.pid, signal.SIGTERM)
                
                # Wait for the process to terminate
                try:
                    self.process.wait(timeout=5)
                    logger.info("MCP server terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("MCP server did not terminate gracefully, killing")
                    if os.name == 'nt':  # Windows
                        self.process.kill()
                    else:  # Unix/Linux/Mac
                        os.kill(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=5)
                    logger.info("MCP server killed")
            except Exception as e:
                logger.error(f"Error stopping MCP server: {str(e)}")
            
            # Clean up
            self.process = None
