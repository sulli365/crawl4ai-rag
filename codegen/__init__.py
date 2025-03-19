"""
Code generation module for the crawl4ai-rag application.
"""

from .generator import CodeGenerator, code_generator

__all__ = ["CodeGenerator", "code_generator", "generate_code"]


async def generate_code(
    url: str,
    purpose: str,
    website_type: str = None,
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
    return await code_generator.generate_from_url(url, purpose, website_type, **kwargs)
