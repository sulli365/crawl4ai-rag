"""
Validation utilities for the crawl4ai-rag application.
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, validator, Field, HttpUrl

from .logging import get_logger

logger = get_logger(__name__)


class ScrapingPurpose(BaseModel):
    """
    Model for validating scraping purpose input.
    """
    description: str = Field(..., min_length=5, max_length=500)
    extract_links: bool = Field(False)
    extract_text: bool = Field(True)
    extract_images: bool = Field(False)
    extract_tables: bool = Field(False)
    max_depth: int = Field(1, ge=0, le=5)
    
    @validator('description')
    def description_must_be_meaningful(cls, v: str) -> str:
        """Validate that the description is meaningful."""
        if len(v.split()) < 3:
            raise ValueError("Description must contain at least 3 words")
        return v


class UrlInput(BaseModel):
    """
    Model for validating URL input.
    """
    url: HttpUrl
    
    @validator('url')
    def url_must_be_valid(cls, v: str) -> str:
        """Validate that the URL is valid."""
        try:
            result = urlparse(v)
            if not all([result.scheme, result.netloc]):
                raise ValueError("URL must have a scheme and netloc")
            return v
        except Exception as e:
            logger.error(f"Invalid URL: {v} - {str(e)}")
            raise ValueError(f"Invalid URL: {v}")


class OutputPreferences(BaseModel):
    """
    Model for validating output preferences.
    """
    output_code: bool = Field(True)
    output_markdown: bool = Field(False)
    markdown_output_dir: Optional[str] = Field(None)


def validate_url(url: str) -> bool:
    """
    Validate that a URL is properly formatted.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if the URL is valid, False otherwise
    """
    try:
        UrlInput(url=url)
        return True
    except Exception:
        return False


def validate_urls(urls: List[str]) -> List[str]:
    """
    Validate a list of URLs and return only the valid ones.
    
    Args:
        urls: List of URLs to validate
        
    Returns:
        List of valid URLs
    """
    valid_urls = []
    for url in urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            logger.warning(f"Skipping invalid URL: {url}")
    
    return valid_urls


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to ensure it's valid across operating systems.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Replace multiple underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure the filename is not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized
