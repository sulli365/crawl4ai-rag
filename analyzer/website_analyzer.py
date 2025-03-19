"""
Website analyzer for the crawl4ai-rag application.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from ..config import settings
from ..utils.logging import get_logger
from ..utils.validation import validate_url, validate_urls
from ..supabase.repository import PageRepository

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
                
                # Extract data based on preferences
                analysis = {
                    "url": url,
                    "title": result.title,
                    "markdown": result.markdown_v2.raw_markdown if extract_text else "",
                    "links": {
                        "internal": result.links["internal"] if extract_links else [],
                        "external": result.links["external"] if extract_links else []
                    },
                    "structure": self._analyze_structure(result.markdown_v2.raw_markdown) if extract_text else {},
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
        
        return {
            "headings": headings,
            "code_blocks": code_blocks,
            "link_count": link_count,
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes
        }
    
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
        
        return {
            "total_pages": total_pages,
            "total_internal_links": total_internal_links,
            "total_external_links": total_external_links,
            "link_structure": link_structure
        }


# Create a global instance of the website analyzer
website_analyzer = WebsiteAnalyzer()
