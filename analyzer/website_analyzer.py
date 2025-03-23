"""
Website analyzer for the crawl4ai-rag application.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from config import settings
from utils.logging import get_logger
from utils.validation import validate_url, validate_urls, validate_documentation_structure, validate_code_blocks
from db_client.repository import PageRepository

logger = get_logger(__name__)


class WebsiteAnalyzer:
    """
    Analyzer for website structure and content.
    """
    
    def __init__(self):
        """Initialize the website analyzer."""
        self.page_repo = PageRepository()
        
        # Configure browser
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
    
    async def analyze_url(
        self, 
        url: str, 
        max_depth: int = 1,
        extract_links: bool = True,
        extract_text: bool = True,
        extract_images: bool = False,
        extract_tables: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a single URL and return its structure and content.
        
        Args:
            url: The URL to analyze
            max_depth: Maximum crawl depth
            extract_links: Whether to extract links
            extract_text: Whether to extract text
            extract_images: Whether to extract images
            extract_tables: Whether to extract tables
            
        Returns:
            Dictionary with analysis results
        """
        # Validate URL
        if not validate_url(url):
            logger.error(f"Invalid URL: {url}")
            return {"error": f"Invalid URL: {url}"}
        
        try:
            # Configure crawler
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                excluded_tags=['form', 'header'],
                exclude_external_links=True,
                process_iframes=True,
                remove_overlay_elements=True,
            )
            
            # Create the crawler instance
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                # Crawl the URL
                result = await crawler.arun(
                    url=url,
                    config=crawl_config
                )
                
                if not result.success:
                    logger.error(f"Failed to crawl {url}: {result.error_message}")
                    return {"error": f"Failed to crawl {url}: {result.error_message}"}
                
                # Extract and analyze structure
                markdown_content = result.markdown.raw_markdown if extract_text else ""
                structure_analysis = self._analyze_structure(markdown_content) if extract_text else {}
                
                # Validate documentation structure and code blocks if this is a documentation page
                validation_results = {}
                if extract_text and self._is_likely_documentation(markdown_content, result.title):
                    validation_results["documentation"] = validate_documentation_structure(structure_analysis)
                    if "code_block_types" in structure_analysis:
                        validation_results["code_blocks"] = validate_code_blocks(structure_analysis["code_block_types"])
                
                # Extract data based on preferences
                analysis = {
                    "url": url,
                    "title": result.title,
                    "markdown": markdown_content,
                    "links": {
                        "internal": result.links["internal"] if extract_links else [],
                        "external": result.links["external"] if extract_links else []
                    },
                    "structure": structure_analysis,
                    "validation": validation_results
                }
                
                # Add images if requested
                if extract_images:
                    analysis["images"] = result.images
                
                # Add tables if requested
                if extract_tables and hasattr(result, "tables"):
                    analysis["tables"] = result.tables
                
                logger.info(f"Successfully analyzed: {url}")
                return analysis
                
        except Exception as e:
            logger.error(f"Error analyzing {url}: {str(e)}")
            return {"error": f"Error analyzing {url}: {str(e)}"}
    
    def _analyze_structure(self, markdown: str) -> Dict[str, Any]:
        """
        Analyze the structure of a markdown document.
        
        Args:
            markdown: The markdown content
            
        Returns:
            Dictionary with structure analysis
        """
        # Extract headings
        headings = []
        current_level = 0
        
        for line in markdown.split("\n"):
            if line.startswith("#"):
                # Count the number of # characters
                level = 0
                for char in line:
                    if char == "#":
                        level += 1
                    else:
                        break
                
                # Extract the heading text
                heading_text = line[level:].strip()
                
                headings.append({
                    "level": level,
                    "text": heading_text
                })
        
        # Count code blocks
        code_blocks = markdown.count("```")
        code_blocks = code_blocks // 2  # Each block has opening and closing ```
        
        # Count links
        link_count = markdown.count("](")
        
        # Estimate reading time (average reading speed: 200 words per minute)
        word_count = len(markdown.split())
        reading_time_minutes = max(1, round(word_count / 200))
        
        # Basic structure metrics
        basic_metrics = {
            "headings": headings,
            "code_blocks": code_blocks,
            "link_count": link_count,
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes
        }
        
        # Documentation-specific metrics
        documentation_metrics = {
            "api_sections": self._detect_api_sections(markdown),
            "code_block_types": self._analyze_code_blocks(markdown),
            "example_count": markdown.lower().count("example:"),
            "parameter_tables": self._count_parameter_tables(markdown),
            "has_installation_section": self._has_section(markdown, ["installation", "setup", "getting started"]),
            "has_usage_section": self._has_section(markdown, ["usage", "how to use", "examples"]),
            "has_api_reference": self._has_section(markdown, ["api", "reference", "documentation"]),
        }
        
        return {**basic_metrics, **documentation_metrics}
    
    async def analyze_urls(
        self, 
        urls: List[str], 
        max_depth: int = 1,
        max_concurrent: int = 5,
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple URLs in parallel.
        
        Args:
            urls: List of URLs to analyze
            max_depth: Maximum crawl depth
            max_concurrent: Maximum number of concurrent analyses
            **kwargs: Additional arguments for analyze_url
            
        Returns:
            Dictionary mapping URLs to their analysis results
        """
        # Validate URLs
        valid_urls = validate_urls(urls)
        
        if not valid_urls:
            logger.error("No valid URLs provided")
            return {}
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(url: str) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                result = await self.analyze_url(url, max_depth, **kwargs)
                return url, result
        
        # Analyze all URLs in parallel with limited concurrency
        results = await asyncio.gather(
            *[analyze_with_semaphore(url) for url in valid_urls]
        )
        
        # Convert results to dictionary
        return {url: result for url, result in results}
    
    def _detect_api_sections(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Detect API sections in markdown content.
        
        Args:
            markdown: The markdown content
            
        Returns:
            List of detected API sections with metadata
        """
        api_sections = []
        lines = markdown.split("\n")
        
        # Patterns that indicate API documentation
        api_patterns = [
            r"^\s*#{1,3}\s+.*\bAPI\b",
            r"^\s*#{1,3}\s+.*\bEndpoint\b",
            r"^\s*#{1,3}\s+.*\bMethod\b",
            r"^\s*#{1,3}\s+.*\bFunction\b",
            r"^\s*#{1,3}\s+.*\bClass\b",
            r"^\s*`[^`]+`\s*\(",  # Function signature like `function_name(`
        ]
        
        # Compile patterns for efficiency
        compiled_patterns = [re.compile(pattern) for pattern in api_patterns]
        
        # Track current section
        current_section = None
        
        for i, line in enumerate(lines):
            # Check if line matches any API pattern
            for pattern in compiled_patterns:
                if pattern.search(line):
                    # Extract section name
                    section_name = line.strip("# \t")
                    
                    # If we're already in a section, close it
                    if current_section:
                        current_section["end_line"] = i - 1
                        api_sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        "name": section_name,
                        "start_line": i,
                        "end_line": None,
                        "content_preview": line
                    }
                    break
        
        # Close the last section if there is one
        if current_section:
            current_section["end_line"] = len(lines) - 1
            api_sections.append(current_section)
        
        return api_sections
    
    def _analyze_code_blocks(self, markdown: str) -> Dict[str, Any]:
        """
        Analyze code blocks in markdown content.
        
        Args:
            markdown: The markdown content
            
        Returns:
            Dictionary with code block analysis
        """
        # Extract code blocks with their language
        code_block_pattern = r"```(\w*)\n(.*?)```"
        code_blocks = re.findall(code_block_pattern, markdown, re.DOTALL)
        
        # Count by language
        language_counts = {}
        for lang, _ in code_blocks:
            lang = lang.lower().strip() or "text"  # Default to "text" if no language specified
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Analyze purpose (heuristic)
        purposes = {
            "example": 0,
            "installation": 0,
            "usage": 0,
            "api": 0,
            "other": 0
        }
        
        for lang, content in code_blocks:
            content_lower = content.lower()
            if "install" in content_lower or "pip" in content_lower or "npm" in content_lower:
                purposes["installation"] += 1
            elif "example" in content_lower or "# example" in content_lower:
                purposes["example"] += 1
            elif "import" in content_lower and len(content.split("\n")) > 5:
                purposes["usage"] += 1
            elif "def " in content_lower or "class " in content_lower or "function" in content_lower:
                purposes["api"] += 1
            else:
                purposes["other"] += 1
        
        return {
            "total": len(code_blocks),
            "by_language": language_counts,
            "by_purpose": purposes
        }
    
    def _count_parameter_tables(self, markdown: str) -> int:
        """
        Count parameter tables in markdown content.
        
        Args:
            markdown: The markdown content
            
        Returns:
            Number of parameter tables
        """
        # Look for tables with parameter-related headers
        param_patterns = [
            r"\|\s*Parameter\s*\|",
            r"\|\s*Param\s*\|",
            r"\|\s*Argument\s*\|",
            r"\|\s*Name\s*\|.*\|\s*Description\s*\|",
            r"\|\s*Field\s*\|.*\|\s*Description\s*\|"
        ]
        
        count = 0
        for pattern in param_patterns:
            count += len(re.findall(pattern, markdown, re.IGNORECASE))
        
        return count
    
    def _has_section(self, markdown: str, keywords: List[str]) -> bool:
        """
        Check if markdown has a section with any of the given keywords.
        
        Args:
            markdown: The markdown content
            keywords: List of keywords to check for in section headings
            
        Returns:
            True if a matching section is found, False otherwise
        """
        lines = markdown.split("\n")
        for line in lines:
            if line.startswith("#"):
                heading = line.lower()
                if any(keyword.lower() in heading for keyword in keywords):
                    return True
        return False
    
    async def analyze_website(
        self, 
        url: str, 
        max_depth: int = 1,
        max_urls: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze a website by crawling its pages up to a certain depth.
        
        Args:
            url: The root URL of the website
            max_depth: Maximum crawl depth
            max_urls: Maximum number of URLs to analyze
            **kwargs: Additional arguments for analyze_url
            
        Returns:
            Dictionary with website analysis results
        """
        # Validate URL
        if not validate_url(url):
            logger.error(f"Invalid URL: {url}")
            return {"error": f"Invalid URL: {url}"}
        
        try:
            # Analyze the root URL
            root_analysis = await self.analyze_url(url, max_depth=1, **kwargs)
            
            if "error" in root_analysis:
                return root_analysis
            
            # Extract internal links
            internal_links = [link["href"] for link in root_analysis["links"]["internal"]]
            
            # Limit the number of URLs to analyze
            urls_to_analyze = internal_links[:max_urls - 1]  # -1 because we already analyzed the root URL
            
            # Analyze internal links
            page_analyses = await self.analyze_urls(
                urls_to_analyze, 
                max_depth=1,  # Only analyze the page itself, not its links
                **kwargs
            )
            
            # Combine results
            website_analysis = {
                "root_url": url,
                "title": root_analysis.get("title", ""),
                "pages": {url: root_analysis, **page_analyses},
                "structure": self._analyze_website_structure(root_analysis, page_analyses)
            }
            
            logger.info(f"Successfully analyzed website: {url}")
            return website_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing website {url}: {str(e)}")
            return {"error": f"Error analyzing website {url}: {str(e)}"}
    
    def _is_likely_documentation(self, markdown: str, title: str) -> bool:
        """
        Determine if a page is likely to be documentation based on content and title.
        
        Args:
            markdown: The markdown content
            title: The page title
            
        Returns:
            True if the page is likely documentation, False otherwise
        """
        # Check title for documentation indicators
        title_lower = title.lower()
        title_indicators = ["documentation", "docs", "api", "reference", "guide", "manual", "tutorial"]
        if any(indicator in title_lower for indicator in title_indicators):
            return True
        
        # Check content for documentation indicators
        content_lower = markdown.lower()
        content_indicators = [
            "## installation", "## usage", "## api", "## reference",
            "getting started", "quick start", "# documentation",
            "api reference", "function reference", "class reference"
        ]
        if any(indicator in content_lower for indicator in content_indicators):
            return True
        
        # Check for code blocks and parameter tables
        if "```" in markdown and ("| parameter |" in content_lower or "| param |" in content_lower):
            return True
        
        # Check for API-like headings
        lines = markdown.split("\n")
        api_heading_count = 0
        for line in lines:
            if line.startswith("#") and any(x in line.lower() for x in ["method", "function", "class", "endpoint"]):
                api_heading_count += 1
        
        if api_heading_count >= 2:
            return True
        
        return False
    
    def _analyze_website_structure(
        self, 
        root_analysis: Dict[str, Any], 
        page_analyses: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze the structure of a website based on page analyses.
        
        Args:
            root_analysis: Analysis of the root page
            page_analyses: Analyses of other pages
            
        Returns:
            Dictionary with website structure analysis
        """
        # Count total pages
        total_pages = 1 + len(page_analyses)  # Root page + other pages
        
        # Count total links
        total_internal_links = len(root_analysis["links"]["internal"])
        total_external_links = len(root_analysis["links"]["external"])
        
        for page_url, page_analysis in page_analyses.items():
            if "links" in page_analysis:
                total_internal_links += len(page_analysis["links"]["internal"])
                total_external_links += len(page_analysis["links"]["external"])
        
        # Analyze link structure
        link_structure = {}
        for page_url, page_analysis in {root_analysis["url"]: root_analysis, **page_analyses}.items():
            if "links" in page_analysis:
                link_structure[page_url] = [
                    link["href"] for link in page_analysis["links"]["internal"]
                ]
        
        # Identify documentation pages
        documentation_pages = []
        for page_url, page_analysis in {root_analysis["url"]: root_analysis, **page_analyses}.items():
            if "validation" in page_analysis and "documentation" in page_analysis["validation"]:
                documentation_pages.append({
                    "url": page_url,
                    "title": page_analysis.get("title", ""),
                    "validation": page_analysis["validation"]["documentation"]
                })
        
        # Analyze documentation structure across the website
        documentation_analysis = self._analyze_documentation_structure(documentation_pages) if documentation_pages else {}
        
        return {
            "total_pages": total_pages,
            "total_internal_links": total_internal_links,
            "total_external_links": total_external_links,
            "link_structure": link_structure,
            "documentation_pages": documentation_pages,
            "documentation_analysis": documentation_analysis
        }
    
    def _analyze_documentation_structure(self, documentation_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the documentation structure across multiple pages.
        
        Args:
            documentation_pages: List of documentation pages with validation results
            
        Returns:
            Dictionary with documentation structure analysis
        """
        if not documentation_pages:
            return {}
        
        # Calculate overall documentation quality
        total_score = 0
        total_max_score = 0
        valid_pages = 0
        errors = []
        warnings = []
        
        for page in documentation_pages:
            validation = page.get("validation", {})
            if validation:
                total_score += validation.get("score", 0)
                total_max_score += validation.get("max_score", 0)
                
                if validation.get("is_valid", False):
                    valid_pages += 1
                
                # Collect errors and warnings
                for error in validation.get("errors", []):
                    errors.append({
                        "url": page["url"],
                        "title": page["title"],
                        **error
                    })
                
                for warning in validation.get("warnings", []):
                    warnings.append({
                        "url": page["url"],
                        "title": page["title"],
                        **warning
                    })
        
        # Calculate overall percentage
        overall_percentage = round((total_score / total_max_score * 100) if total_max_score > 0 else 0)
        
        # Determine documentation completeness
        completeness_level = "high" if overall_percentage >= 80 else "medium" if overall_percentage >= 50 else "low"
        
        # Identify documentation gaps
        gaps = []
        if len(documentation_pages) < 3:
            gaps.append("Limited documentation pages")
        
        error_types = set(error.get("code", "") for error in errors)
        if "headings_insufficient" in error_types:
            gaps.append("Insufficient heading structure")
        if "code_blocks_insufficient" in error_types:
            gaps.append("Insufficient code examples")
        if "api_sections_insufficient" in error_types:
            gaps.append("Incomplete API documentation")
        if "parameter_tables_insufficient" in error_types:
            gaps.append("Missing parameter documentation")
        
        return {
            "total_pages": len(documentation_pages),
            "valid_pages": valid_pages,
            "overall_score": total_score,
            "overall_max_score": total_max_score,
            "overall_percentage": overall_percentage,
            "completeness_level": completeness_level,
            "errors": errors,
            "warnings": warnings,
            "gaps": gaps
        }


# Create a global instance of the website analyzer
website_analyzer = WebsiteAnalyzer()
