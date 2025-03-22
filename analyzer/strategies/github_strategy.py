"""
GitHub documentation scraping strategy.
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import re
from urllib.parse import urlparse

from utils.logging import get_logger
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
        
        # Generate code using the GitHub documentation scraper template
        context = {
            "url": url,
            "purpose": purpose,
            "repo_info": self._parse_github_url(url)
        }
        
        return code_generator.generate_from_template("github_docs_scraper.j2", context)
    
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
