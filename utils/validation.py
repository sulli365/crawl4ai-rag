"""
Validation utilities for the crawl4ai-rag application.
"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse
from pydantic import BaseModel, validator, Field, HttpUrl

from .logging import get_logger

logger = get_logger(__name__)


class DocumentationErrorSeverity(str, Enum):
    """Severity levels for documentation validation errors."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DocumentationErrorCode(str, Enum):
    """Error codes for documentation validation errors."""
    MISSING_SECTIONS = "missing_sections"
    INSUFFICIENT_EXAMPLES = "insufficient_examples"
    INCOMPLETE_API_DOCS = "incomplete_api_docs"
    MISSING_CODE_BLOCKS = "missing_code_blocks"
    INVALID_CODE_BLOCKS = "invalid_code_blocks"
    MISSING_PARAMETER_TABLES = "missing_parameter_tables"
    STRUCTURE_ERROR = "structure_error"


class DocumentationError(Exception):
    """Base class for documentation validation errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Union[DocumentationErrorCode, str],
        severity: Union[DocumentationErrorSeverity, str] = DocumentationErrorSeverity.WARNING,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize a documentation error."""
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.details = details or {}
        super().__init__(message)


def validate_documentation_structure(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate minimum documentation requirements and return validation results.
    
    Args:
        analysis: Dictionary with document structure analysis
        
    Returns:
        Dictionary with validation results
    """
    # Define minimum requirements
    requirements = {
        "headings": {
            "min_count": 3,
            "severity": DocumentationErrorSeverity.ERROR,
            "message": "Documentation should have at least 3 headings for proper structure"
        },
        "code_blocks": {
            "min_count": 1,
            "severity": DocumentationErrorSeverity.ERROR,
            "message": "Documentation should include at least 1 code block"
        },
        "example_count": {
            "min_count": 1,
            "severity": DocumentationErrorSeverity.WARNING,
            "message": "Documentation should include at least 1 example"
        },
        "api_sections": {
            "min_count": 1,
            "severity": DocumentationErrorSeverity.WARNING,
            "message": "Documentation should include API sections"
        },
        "parameter_tables": {
            "min_count": 1,
            "severity": DocumentationErrorSeverity.WARNING,
            "message": "Documentation should include parameter tables"
        }
    }
    
    # Check each requirement
    validation_results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "score": 0,
        "max_score": len(requirements)
    }
    
    for key, req in requirements.items():
        # Get the actual value (count)
        if key == "api_sections" and key in analysis:
            actual = len(analysis[key])
        elif key == "headings" and key in analysis:
            actual = len(analysis[key])
        else:
            actual = analysis.get(key, 0)
        
        # Check if it meets the requirement
        if actual < req["min_count"]:
            error = {
                "code": f"{key}_insufficient",
                "message": req["message"],
                "severity": req["severity"],
                "actual": actual,
                "expected": req["min_count"]
            }
            
            if req["severity"] == DocumentationErrorSeverity.ERROR:
                validation_results["is_valid"] = False
                validation_results["errors"].append(error)
            else:
                validation_results["warnings"].append(error)
        else:
            validation_results["score"] += 1
    
    # Add section-specific validations
    if analysis.get("has_installation_section", False):
        validation_results["score"] += 0.5
        validation_results["max_score"] += 0.5
    
    if analysis.get("has_usage_section", False):
        validation_results["score"] += 0.5
        validation_results["max_score"] += 0.5
    
    if analysis.get("has_api_reference", False):
        validation_results["score"] += 0.5
        validation_results["max_score"] += 0.5
    
    # Calculate percentage score
    validation_results["percentage"] = round(
        (validation_results["score"] / validation_results["max_score"]) * 100
    )
    
    return validation_results


def validate_code_blocks(code_blocks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate code blocks in documentation.
    
    Args:
        code_blocks: Dictionary with code block analysis
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "score": 0,
        "max_score": 3  # Language diversity, purpose coverage, total count
    }
    
    # Check total number of code blocks
    if code_blocks.get("total", 0) < 3:
        validation_results["warnings"].append({
            "code": "insufficient_code_blocks",
            "message": "Documentation should have at least 3 code blocks for comprehensive examples",
            "severity": DocumentationErrorSeverity.WARNING,
            "actual": code_blocks.get("total", 0),
            "expected": 3
        })
    else:
        validation_results["score"] += 1
    
    # Check language diversity
    language_count = len(code_blocks.get("by_language", {}))
    if language_count < 2:
        validation_results["warnings"].append({
            "code": "limited_language_diversity",
            "message": "Documentation should include examples in multiple languages",
            "severity": DocumentationErrorSeverity.WARNING,
            "actual": language_count,
            "expected": 2
        })
    else:
        validation_results["score"] += 1
    
    # Check purpose coverage
    purposes = code_blocks.get("by_purpose", {})
    covered_purposes = sum(1 for p, count in purposes.items() if p != "other" and count > 0)
    if covered_purposes < 2:
        validation_results["warnings"].append({
            "code": "limited_purpose_coverage",
            "message": "Documentation should include code examples for different purposes (installation, usage, API)",
            "severity": DocumentationErrorSeverity.WARNING,
            "actual": covered_purposes,
            "expected": 2
        })
    else:
        validation_results["score"] += 1
    
    # Calculate percentage score
    validation_results["percentage"] = round(
        (validation_results["score"] / validation_results["max_score"]) * 100
    )
    
    return validation_results


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
    def url_must_be_valid(cls, v: HttpUrl) -> HttpUrl:
        """Validate that the URL is valid."""
        try:
            # Convert HttpUrl to string for urlparse
            url_str = str(v)
            result = urlparse(url_str)
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
