"""
Markdown exporter for the crawl4ai-rag application.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from config import settings
from utils.logging import get_logger
from utils.validation import sanitize_filename
from analyzer import analyze_website, generate_markdown

logger = get_logger(__name__)


class MarkdownExporter:
    """
    Exporter for generating markdown files from website content.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the markdown exporter.
        
        Args:
            output_dir: Directory to write markdown files
        """
        self.output_dir = output_dir or settings.default_markdown_output_dir
    
    async def export_from_url(
        self, 
        url: str, 
        output_dir: Optional[str] = None,
        website_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Export markdown files from a website URL.
        
        Args:
            url: The URL to analyze
            output_dir: Directory to write markdown files
            website_type: The type of website (e.g., "ecommerce", "documentation", "blog")
            **kwargs: Additional arguments for the analysis
            
        Returns:
            Dictionary mapping filenames to file paths
        """
        # Use specified output directory or default
        output_dir = output_dir or self.output_dir
        
        # Analyze the website
        analysis = await analyze_website(url, website_type, **kwargs)
        
        # Generate markdown
        markdown_files = await generate_markdown(analysis, website_type)
        
        # Write markdown files to disk
        return self.write_markdown_files(markdown_files, output_dir)
    
    async def export_from_analysis(
        self, 
        analysis: Dict[str, Any],
        output_dir: Optional[str] = None,
        website_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export markdown files from an existing analysis.
        
        Args:
            analysis: The analysis results
            output_dir: Directory to write markdown files
            website_type: The type of website (e.g., "ecommerce", "documentation", "blog")
            
        Returns:
            Dictionary mapping filenames to file paths
        """
        # Use specified output directory or default
        output_dir = output_dir or self.output_dir
        
        # Generate markdown
        markdown_files = await generate_markdown(analysis, website_type)
        
        # Write markdown files to disk
        return self.write_markdown_files(markdown_files, output_dir)
    
    def write_markdown_files(
        self, 
        markdown_files: Dict[str, str],
        output_dir: str
    ) -> Dict[str, str]:
        """
        Write markdown files to disk.
        
        Args:
            markdown_files: Dictionary mapping filenames to markdown content
            output_dir: Directory to write markdown files
            
        Returns:
            Dictionary mapping filenames to file paths
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        result = {}
        
        for filename, content in markdown_files.items():
            try:
                # Sanitize filename
                safe_filename = sanitize_filename(filename)
                
                # Ensure filename has .md extension
                if not safe_filename.endswith(".md"):
                    safe_filename += ".md"
                
                # Create file path
                file_path = os.path.join(output_dir, safe_filename)
                
                # Write content to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Add to result
                result[safe_filename] = file_path
                
                logger.info(f"Wrote markdown file: {file_path}")
            except Exception as e:
                logger.error(f"Error writing markdown file {filename}: {str(e)}")
        
        return result
    
    def write_markdown_file(
        self, 
        filename: str,
        content: str,
        output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Write a single markdown file to disk.
        
        Args:
            filename: The filename
            content: The markdown content
            output_dir: Directory to write markdown file
            
        Returns:
            The file path or None if failed
        """
        # Use specified output directory or default
        output_dir = output_dir or self.output_dir
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Sanitize filename
            safe_filename = sanitize_filename(filename)
            
            # Ensure filename has .md extension
            if not safe_filename.endswith(".md"):
                safe_filename += ".md"
            
            # Create file path
            file_path = os.path.join(output_dir, safe_filename)
            
            # Write content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Wrote markdown file: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error writing markdown file {filename}: {str(e)}")
            return None
    
    def read_markdown_file(self, file_path: str) -> Optional[str]:
        """
        Read a markdown file from disk.
        
        Args:
            file_path: The file path
            
        Returns:
            The markdown content or None if failed
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading markdown file {file_path}: {str(e)}")
            return None
    
    def list_markdown_files(self, directory: Optional[str] = None) -> List[str]:
        """
        List all markdown files in a directory.
        
        Args:
            directory: The directory to list
            
        Returns:
            List of file paths
        """
        directory = directory or self.output_dir
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # List all markdown files
            return [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if f.endswith(".md")
            ]
        except Exception as e:
            logger.error(f"Error listing markdown files in {directory}: {str(e)}")
            return []


# Create a global instance of the markdown exporter
markdown_exporter = MarkdownExporter()
