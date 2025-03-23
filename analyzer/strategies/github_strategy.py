"""
GitHub documentation scraping strategy.
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import re
from urllib.parse import urlparse

from utils.logging import get_logger
from utils.mcp_client import McpClient
from . import DocumentationStrategy

logger = get_logger(__name__)


class GitHubDocumentationStrategy(DocumentationStrategy):
    """
    Scraping strategy for GitHub documentation websites.
    """
    
    async def generate_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate code for scraping a GitHub documentation website.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Generated code as a string
        """
        if "error" in analysis:
            return f"# Error: {analysis['error']}"
        
        # Import the code generator
        from codegen.generator import code_generator
        
        # Extract URL and purpose
        url = analysis.get("root_url", "")
        purpose = analysis.get("purpose", "Extract GitHub documentation")
        
        # Check if this is a GitHub URL
        if not self._is_github_url(url):
            logger.warning(f"URL {url} is not a GitHub URL, using generic documentation template")
            return await super().generate_code(analysis)
        
        # Parse GitHub URL to get repository information
        repo_info = self._parse_github_url(url)
        
        # Enhance repo_info with additional data from GitHub MCP if possible
        try:
            # Get repository information using GitHub MCP
            mcp_result = await McpClient.use_github_mcp(
                "search_repositories",
                {
                    "query": f"repo:{repo_info['owner']}/{repo_info['repo']}"
                }
            )
            
            if not "error" in mcp_result and mcp_result.get("items"):
                repo_data = mcp_result["items"][0]
                repo_info.update({
                    "description": repo_data.get("description", ""),
                    "stars": repo_data.get("stargazers_count", 0),
                    "forks": repo_data.get("forks_count", 0),
                    "default_branch": repo_data.get("default_branch", "main"),
                    "has_issues": repo_data.get("has_issues", False),
                    "has_wiki": repo_data.get("has_wiki", False)
                })
                
                # Update branch if we're using the default branch
                if repo_info["branch"] == "main" and repo_data.get("default_branch") != "main":
                    repo_info["branch"] = repo_data.get("default_branch")
                    
                logger.info(f"Enhanced repo info with GitHub MCP data for {repo_info['full_repo']}")
        except Exception as e:
            logger.warning(f"Failed to enhance repo info with GitHub MCP: {str(e)}")
        
        # Generate code using the GitHub documentation scraper template
        context = {
            "url": url,
            "purpose": purpose,
            "repo_info": repo_info,
            "use_mcp": True  # Flag to indicate MCP should be used
        }
        
        return code_generator.generate_from_template("github_docs_scraper.j2", context)
    
    async def analyze_repository(self, url: str) -> Dict[str, Any]:
        """
        Analyze a GitHub repository using MCP.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Analysis results
        """
        try:
            # Parse GitHub URL
            repo_info = self._parse_github_url(url)
            
            # Get repository information
            repo_result = await McpClient.use_github_mcp(
                "search_repositories",
                {
                    "query": f"repo:{repo_info['owner']}/{repo_info['repo']}"
                }
            )
            
            if "error" in repo_result:
                logger.error(f"Error getting repository info: {repo_result['error']}")
                return {"error": f"Failed to analyze repository: {repo_result['error']}"}
            
            if not repo_result.get("items"):
                logger.error(f"Repository {repo_info['full_repo']} not found")
                return {"error": f"Repository {repo_info['full_repo']} not found"}
            
            repo_data = repo_result["items"][0]
            
            # Get README content
            readme_result = await McpClient.use_github_mcp(
                "get_file_contents",
                {
                    "owner": repo_info["owner"],
                    "repo": repo_info["repo"],
                    "path": "README.md",
                    "branch": repo_info["branch"]
                }
            )
            
            readme_content = ""
            if not "error" in readme_result and readme_result.get("content"):
                # Decode content if it's base64 encoded
                content = readme_result.get("content", "")
                if readme_result.get("encoding") == "base64":
                    import base64
                    readme_content = base64.b64decode(content).decode("utf-8")
                else:
                    readme_content = content
            
            # Get repository structure (list of files)
            files = []
            try:
                # This is a simplified approach - in a real implementation,
                # you would recursively get all files
                root_contents = await McpClient.use_github_mcp(
                    "get_file_contents",
                    {
                        "owner": repo_info["owner"],
                        "repo": repo_info["repo"],
                        "path": "",
                        "branch": repo_info["branch"]
                    }
                )
                
                if not "error" in root_contents and isinstance(root_contents, list):
                    files = [item.get("path") for item in root_contents if item.get("type") == "file"]
            except Exception as e:
                logger.warning(f"Error getting repository structure: {str(e)}")
            
            # Prepare analysis results
            analysis = {
                "url": url,
                "repo_info": {
                    "owner": repo_info["owner"],
                    "repo": repo_info["repo"],
                    "branch": repo_info["branch"],
                    "full_repo": repo_info["full_repo"],
                    "description": repo_data.get("description", ""),
                    "stars": repo_data.get("stargazers_count", 0),
                    "forks": repo_data.get("forks_count", 0),
                    "default_branch": repo_data.get("default_branch", "main"),
                    "has_issues": repo_data.get("has_issues", False),
                    "has_wiki": repo_data.get("has_wiki", False),
                    "license": repo_data.get("license", {}).get("name", "")
                },
                "readme": readme_content,
                "files": files,
                "has_documentation": self._has_documentation(files)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {str(e)}")
            return {"error": f"Failed to analyze repository: {str(e)}"}
    
    def _has_documentation(self, files: List[str]) -> bool:
        """
        Check if a repository has documentation files.
        
        Args:
            files: List of file paths
            
        Returns:
            True if documentation files are found, False otherwise
        """
        doc_patterns = [
            r"^docs/",
            r"^documentation/",
            r"^wiki/",
            r"\.md$",
            r"\.rst$",
            r"^README",
            r"^CONTRIBUTING",
            r"^CHANGELOG",
            r"^LICENSE"
        ]
        
        for file in files:
            for pattern in doc_patterns:
                if re.search(pattern, file, re.IGNORECASE):
                    return True
        
        return False
    
    def _is_github_url(self, url: str) -> bool:
        """
        Check if a URL is a GitHub URL.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is a GitHub URL, False otherwise
        """
        parsed = urlparse(url)
        return parsed.netloc == "github.com" or parsed.netloc.endswith(".github.com")
    
    def _parse_github_url(self, url: str) -> Dict[str, str]:
        """
        Parse a GitHub URL to extract repository information.
        
        Args:
            url: GitHub URL
            
        Returns:
            Dictionary with repository information
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        if len(path_parts) < 2:
            return {
                "owner": "",
                "repo": "",
                "branch": "main",
                "path": "",
                "full_repo": ""
            }
        
        owner = path_parts[0]
        repo = path_parts[1]
        
        # Determine if this is a specific path within the repo
        path = "/".join(path_parts[2:]) if len(path_parts) > 2 else ""
        
        # Determine if this is a specific branch
        branch = "main"  # Default branch
        if len(path_parts) > 4 and path_parts[2] == "tree":
            branch = path_parts[3]
            path = "/".join(path_parts[4:])
        
        return {
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "path": path,
            "full_repo": f"{owner}/{repo}"
        }
