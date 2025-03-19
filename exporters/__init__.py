"""
Exporters module for the crawl4ai-rag application.
"""

from .markdown_exporter import MarkdownExporter, markdown_exporter

__all__ = ["MarkdownExporter", "markdown_exporter", "export_markdown"]


async def export_markdown(
    url: str,
    output_dir: str = None,
    website_type: str = None,
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
    return await markdown_exporter.export_from_url(url, output_dir, website_type, **kwargs)
