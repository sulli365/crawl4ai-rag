"""
Website analyzer module for the crawl4ai-rag application.
"""

from typing import List, Dict, Any, Optional, Tuple

from .website_analyzer import WebsiteAnalyzer, website_analyzer
from .strategies import create_strategy, ScrapingStrategy

__all__ = ["analyze_website", "generate_code", "generate_markdown", "detect_website_type"]


async def analyze_website(
    url: str,
    website_type: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Analyze a website using the appropriate strategy.
    
    Args:
        url: The URL to analyze
        website_type: The type of website (e.g., "ecommerce", "documentation", "blog", "github")
        **kwargs: Additional arguments for the analysis
        
    Returns:
        Dictionary with analysis results
    """
    # Detect website type if not provided
    if website_type is None:
        website_type = await detect_website_type(url)
    
    # Create strategy
    strategy = create_strategy(website_type, url)
    
    # Analyze website
    analysis = await strategy.analyze(url, **kwargs)
    
    # Add website type to analysis
    analysis["website_type"] = website_type
    
    return analysis


async def generate_code(
    analysis: Dict[str, Any],
    website_type: Optional[str] = None
) -> str:
    """
    Generate code for scraping based on the analysis.
    
    Args:
        analysis: The analysis results
        website_type: The type of website (e.g., "ecommerce", "documentation", "blog", "github")
        
    Returns:
        Generated code as a string
    """
    # Use website type from analysis if not provided
    if website_type is None:
        website_type = analysis.get("website_type", "generic")
    
    # Get URL from analysis
    url = analysis.get("root_url", "")
    
    # Create strategy
    strategy = create_strategy(website_type, url)
    
    # Generate code
    return await strategy.generate_code(analysis)


async def generate_markdown(
    analysis: Dict[str, Any],
    website_type: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate markdown content based on the analysis.
    
    Args:
        analysis: The analysis results
        website_type: The type of website (e.g., "ecommerce", "documentation", "blog", "github")
        
    Returns:
        Dictionary mapping filenames to markdown content
    """
    # Use website type from analysis if not provided
    if website_type is None:
        website_type = analysis.get("website_type", "generic")
    
    # Get URL from analysis
    url = analysis.get("root_url", "")
    
    # Create strategy
    strategy = create_strategy(website_type, url)
    
    # Generate markdown
    return await strategy.generate_markdown(analysis)


async def detect_website_type(url: str) -> str:
    """
    Detect the type of website based on its URL and content.
    
    Args:
        url: The URL to analyze
        
    Returns:
        The detected website type
    """
    # Analyze the URL
    analysis = await website_analyzer.analyze_url(url)
    
    if "error" in analysis:
        return "generic"
    
    # Check URL patterns
    url_lower = url.lower()
    
    # Check for GitHub patterns
    if "github.com" in url_lower:
        return "github"
    
    # Check for e-commerce patterns
    ecommerce_patterns = [
        "/shop", "/store", "/product", "/cart", "/checkout",
        "amazon", "ebay", "etsy", "shopify", "woocommerce"
    ]
    for pattern in ecommerce_patterns:
        if pattern in url_lower:
            return "ecommerce"
    
    # Check for documentation patterns
    documentation_patterns = [
        "/docs", "/documentation", "/guide", "/manual", "/reference",
        "/api", "/developer", "/sdk", "/tutorial"
    ]
    for pattern in documentation_patterns:
        if pattern in url_lower:
            return "documentation"
    
    # Check for blog patterns
    blog_patterns = [
        "/blog", "/post", "/article", "/news", "/journal",
        "wordpress", "medium", "blogger"
    ]
    for pattern in blog_patterns:
        if pattern in url_lower:
            return "blog"
    
    # Check content patterns
    if "markdown" in analysis:
        content_lower = analysis["markdown"].lower()
        
        # Check for e-commerce content patterns
        if any(pattern in content_lower for pattern in ["add to cart", "product description", "price", "shipping", "checkout"]):
            return "ecommerce"
        
        # Check for documentation content patterns
        if any(pattern in content_lower for pattern in ["documentation", "api reference", "getting started", "installation", "usage"]):
            return "documentation"
        
        # Check for blog content patterns
        if any(pattern in content_lower for pattern in ["posted on", "author", "comments", "tags", "categories"]):
            return "blog"
    
    # Default to generic
    return "generic"
