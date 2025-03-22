"""
Code generator for the crawl4ai-rag application.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from config import settings
from utils.logging import get_logger
from analyzer import analyze_website, generate_code

logger = get_logger(__name__)


class CodeGenerator:
    """
    Generator for scraping code based on website analysis.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the code generator.
        
        Args:
            templates_dir: Directory containing code templates
        """
        self.templates_dir = templates_dir or os.path.join(os.path.dirname(__file__), "templates")
        
        # Create templates directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def generate_from_url(
        self, 
        url: str, 
        purpose: str,
        website_type: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate code for scraping a website based on its URL and purpose.
        
        Args:
            url: The URL to analyze
            purpose: The purpose of the scraping
            website_type: The type of website (e.g., "ecommerce", "documentation", "blog")
            **kwargs: Additional arguments for the analysis
            
        Returns:
            Generated code as a string
        """
        # Analyze the website
        analysis = await analyze_website(url, website_type, **kwargs)
        
        # Add purpose to analysis
        analysis["purpose"] = purpose
        
        # Generate code
        return await generate_code(analysis, website_type)
    
    async def generate_from_analysis(
        self, 
        analysis: Dict[str, Any],
        purpose: Optional[str] = None,
        website_type: Optional[str] = None
    ) -> str:
        """
        Generate code for scraping a website based on an existing analysis.
        
        Args:
            analysis: The analysis results
            purpose: The purpose of the scraping
            website_type: The type of website (e.g., "ecommerce", "documentation", "blog")
            
        Returns:
            Generated code as a string
        """
        # Add purpose to analysis if provided
        if purpose is not None:
            analysis["purpose"] = purpose
        
        # Generate code
        return await generate_code(analysis, website_type)
    
    def generate_from_template(
        self, 
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate code using a specific template.
        
        Args:
            template_name: Name of the template file
            context: Context variables for the template
            
        Returns:
            Generated code as a string
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error generating code from template {template_name}: {str(e)}")
            return f"# Error generating code: {str(e)}"
    
    def generate_from_string_template(
        self, 
        template_string: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate code using a template string.
        
        Args:
            template_string: The template string
            context: Context variables for the template
            
        Returns:
            Generated code as a string
        """
        try:
            template = Template(template_string)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error generating code from template string: {str(e)}")
            return f"# Error generating code: {str(e)}"
    
    def save_template(
        self, 
        template_name: str,
        template_content: str
    ) -> bool:
        """
        Save a template to the templates directory.
        
        Args:
            template_name: Name of the template file
            template_content: Content of the template
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure template has .j2 extension
            if not template_name.endswith(".j2"):
                template_name += ".j2"
            
            # Save template
            template_path = os.path.join(self.templates_dir, template_name)
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(template_content)
            
            logger.info(f"Saved template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template {template_name}: {str(e)}")
            return False
    
    def get_template_names(self) -> List[str]:
        """
        Get a list of available template names.
        
        Returns:
            List of template names
        """
        try:
            return self.env.list_templates()
        except Exception as e:
            logger.error(f"Error getting template names: {str(e)}")
            return []
    
    def get_template_content(self, template_name: str) -> Optional[str]:
        """
        Get the content of a template.
        
        Args:
            template_name: Name of the template file
            
        Returns:
            Template content or None if not found
        """
        try:
            # Ensure template has .j2 extension
            if not template_name.endswith(".j2"):
                template_name += ".j2"
            
            # Get template path
            template_path = os.path.join(self.templates_dir, template_name)
            
            # Read template content
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error getting template content for {template_name}: {str(e)}")
            return None


# Create a global instance of the code generator
code_generator = CodeGenerator()
