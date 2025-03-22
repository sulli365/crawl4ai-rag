"""
Scraping strategies for different website types and purposes.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from ...utils.logging import get_logger

logger = get_logger(__name__)


class ScrapingStrategy(ABC):
    """
    Abstract base class for scraping strategies.
    """
    
    @abstractmethod
    async def analyze(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze a website using this strategy.
        
        Args:
            url: The URL to analyze
            **kwargs: Additional arguments for the analysis
            
        Returns:
            Dictionary with analysis results
        """
        pass
    
    @abstractmethod
    async def generate_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate code for scraping based on the analysis.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Generated code as a string
        """
        pass
    
    @abstractmethod
    async def generate_markdown(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate markdown content based on the analysis.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Dictionary mapping filenames to markdown content
        """
        pass


class GenericStrategy(ScrapingStrategy):
    """
    Generic scraping strategy for any website.
    """
    
    def __init__(self):
        """Initialize the generic strategy."""
        from ..website_analyzer import website_analyzer
        self.website_analyzer = website_analyzer
    
    async def analyze(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze a website using the generic strategy.
        
        Args:
            url: The URL to analyze
            **kwargs: Additional arguments for the analysis
            
        Returns:
            Dictionary with analysis results
        """
        return await self.website_analyzer.analyze_website(url, **kwargs)
    
    async def generate_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate code for scraping based on the analysis.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Generated code as a string
        """
        if "error" in analysis:
            return f"# Error: {analysis['error']}"
        
        # Generate code for crawling the website
        code = """
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def crawl_website():
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    
    # Configure crawler
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=['form', 'header'],
        exclude_external_links=True,
        process_iframes=True,
        remove_overlay_elements=True,
    )
    
    # Create the crawler instance
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Crawl the URL
        result = await crawler.arun(
            url="{url}",
            config=crawl_config
        )
        
        if not result.success:
            print(f"Failed to crawl: {{result.error_message}}")
            return
        
        # Print the title
        print(f"Title: {{result.title}}")
        
        # Print the first 500 characters of the markdown content
        print("\\nContent (first 500 chars):")
        print("-" * 50)
        print(result.markdown_v2.raw_markdown[:500])
        print("-" * 50)
        
        # Print internal links
        print("\\nInternal links found:")
        for link in result.links["internal"]:
            print(f"- {{link['href']}}")
        
        # Return the result for further processing
        return result

# Run the crawler
if __name__ == "__main__":
    asyncio.run(crawl_website())
""".format(url=analysis["root_url"])
        
        return code
    
    async def generate_markdown(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate markdown content based on the analysis.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Dictionary mapping filenames to markdown content
        """
        if "error" in analysis:
            return {"error.md": f"# Error\n\n{analysis['error']}"}
        
        result = {}
        
        # Generate main markdown file
        main_content = f"# {analysis.get('title', 'Website Analysis')}\n\n"
        main_content += f"URL: {analysis['root_url']}\n\n"
        
        # Add structure information
        structure = analysis.get("structure", {})
        main_content += f"## Website Structure\n\n"
        main_content += f"- Total Pages: {structure.get('total_pages', 0)}\n"
        main_content += f"- Internal Links: {structure.get('total_internal_links', 0)}\n"
        main_content += f"- External Links: {structure.get('total_external_links', 0)}\n\n"
        
        # Add page list
        main_content += f"## Pages\n\n"
        for page_url, page_analysis in analysis.get("pages", {}).items():
            page_title = page_analysis.get("title", page_url)
            main_content += f"- [{page_title}]({page_url})\n"
        
        result["index.md"] = main_content
        
        # Generate individual page files
        for page_url, page_analysis in analysis.get("pages", {}).items():
            if "markdown" in page_analysis:
                # Create a filename from the URL
                filename = page_url.split("/")[-1]
                if not filename or filename.endswith("/"):
                    filename = "index"
                filename = f"{filename}.md"
                
                # Add the page content
                result[filename] = page_analysis["markdown"]
        
        return result


class EcommerceStrategy(GenericStrategy):
    """
    Scraping strategy for e-commerce websites.
    """
    
    async def generate_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate code for scraping an e-commerce website.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Generated code as a string
        """
        if "error" in analysis:
            return f"# Error: {analysis['error']}"
        
        # Generate code for crawling the e-commerce website
        code = """
import asyncio
import json
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

class Product:
    def __init__(self, name: str, price: str, url: str, image_url: str = None, description: str = None):
        self.name = name
        self.price = price
        self.url = url
        self.image_url = image_url
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "url": self.url,
            "image_url": self.image_url,
            "description": self.description
        }

async def extract_products(url: str) -> List[Product]:
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    
    # Configure crawler
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=['form', 'header'],
        exclude_external_links=True,
        process_iframes=True,
        remove_overlay_elements=True,
    )
    
    products = []
    
    # Create the crawler instance
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Crawl the URL
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        
        if not result.success:
            print(f"Failed to crawl: {{result.error_message}}")
            return products
        
        # Extract product information from the page
        # This is a generic implementation that needs to be customized for the specific website
        
        # Example: Extract products from the page
        # You'll need to adjust the selectors based on the actual website structure
        for product_element in result.soup.select(".product"):
            name = product_element.select_one(".product-name").text.strip()
            price = product_element.select_one(".product-price").text.strip()
            product_url = product_element.select_one("a")["href"]
            image_url = product_element.select_one("img")["src"] if product_element.select_one("img") else None
            
            # Create a product object
            product = Product(
                name=name,
                price=price,
                url=product_url,
                image_url=image_url
            )
            
            products.append(product)
        
        return products

async def crawl_ecommerce_website():
    # URL of the e-commerce website
    url = "{url}"
    
    # Extract products
    products = await extract_products(url)
    
    # Print the results
    print(f"Found {{len(products)}} products")
    for product in products:
        print(f"- {{product.name}}: {{product.price}}")
    
    # Save to JSON file
    with open("products.json", "w") as f:
        json.dump([p.to_dict() for p in products], f, indent=2)
    
    print(f"Saved {{len(products)}} products to products.json")

# Run the crawler
if __name__ == "__main__":
    asyncio.run(crawl_ecommerce_website())
""".format(url=analysis["root_url"])
        
        return code


class DocumentationStrategy(GenericStrategy):
    """
    Scraping strategy for documentation websites.
    """
    
    async def generate_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate code for scraping a documentation website.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Generated code as a string
        """
        if "error" in analysis:
            return f"# Error: {analysis['error']}"
        
        # Generate code for crawling the documentation website
        code = """
import asyncio
import os
from typing import List, Dict, Any
from urllib.parse import urljoin
from xml.etree import ElementTree
import httpx
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def get_sitemap_urls(base_url: str) -> List[str]:
    \"\"\"
    Get URLs from the sitemap.
    
    Args:
        base_url: The base URL of the documentation website
        
    Returns:
        List of URLs
    \"\"\"
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(sitemap_url)
            response.raise_for_status()
            
            # Parse the XML
            root = ElementTree.fromstring(response.content)
            
            # Extract all URLs from the sitemap
            namespace = {{'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}}
            urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
            
            print(f"Found {{len(urls)}} URLs in sitemap")
            return urls
            
    except Exception as e:
        print(f"Error fetching sitemap: {{e}}")
        return []

async def crawl_url(url: str) -> str:
    \"\"\"
    Crawl a single URL and return its markdown content.
    
    Args:
        url: The URL to crawl
        
    Returns:
        Markdown content or empty string if failed
    \"\"\"
    try:
        # Configure browser
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        
        # Configure crawler
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            excluded_tags=['form', 'header'],
            exclude_external_links=True,
            process_iframes=True,
            remove_overlay_elements=True,
        )
        
        # Create the crawler instance
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Crawl the URL
            result = await crawler.arun(
                url=url,
                config=crawl_config
            )
            
            if result.success:
                print(f"Successfully crawled: {{url}}")
                return result.markdown_v2.raw_markdown
            else:
                print(f"Failed to crawl {{url}}: {{result.error_message}}")
                return ""
                
    except Exception as e:
        print(f"Error crawling {{url}}: {{str(e)}}")
        return ""

async def save_markdown(url: str, markdown: str, output_dir: str) -> str:
    \"\"\"
    Save markdown content to a file.
    
    Args:
        url: The URL of the page
        markdown: The markdown content
        output_dir: The output directory
        
    Returns:
        The path to the saved file
    \"\"\"
    try:
        # Create a filename from the URL
        path = url.split("//")[1].split("/")
        filename = path[-1] if path[-1] else "index"
        if not filename.endswith(".md"):
            filename += ".md"
        
        # Create subdirectories if needed
        if len(path) > 1:
            subdir = os.path.join(output_dir, *path[:-1])
            os.makedirs(subdir, exist_ok=True)
            filepath = os.path.join(subdir, filename)
        else:
            filepath = os.path.join(output_dir, filename)
        
        # Save the markdown content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        print(f"Saved markdown to {{filepath}}")
        return filepath
        
    except Exception as e:
        print(f"Error saving markdown for {{url}}: {{str(e)}}")
        return ""

async def crawl_documentation_website():
    # URL of the documentation website
    base_url = "{url}"
    
    # Output directory for markdown files
    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get URLs from sitemap
    urls = await get_sitemap_urls(base_url)
    
    if not urls:
        print("No URLs found in sitemap")
        return
    
    # Crawl each URL and save the markdown
    for url in urls:
        markdown = await crawl_url(url)
        if markdown:
            await save_markdown(url, markdown, output_dir)
    
    print(f"Completed crawling {{len(urls)}} documentation pages")

# Run the crawler
if __name__ == "__main__":
    asyncio.run(crawl_documentation_website())
""".format(url=analysis["root_url"])
        
        return code


class BlogStrategy(GenericStrategy):
    """
    Scraping strategy for blog websites.
    """
    
    async def generate_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate code for scraping a blog website.
        
        Args:
            analysis: The analysis results
            
        Returns:
            Generated code as a string
        """
        if "error" in analysis:
            return f"# Error: {analysis['error']}"
        
        # Generate code for crawling the blog website
        code = """
import asyncio
import json
import os
from typing import List, Dict, Any
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

class BlogPost:
    def __init__(self, title: str, url: str, content: str, date: str = None, author: str = None, categories: List[str] = None):
        self.title = title
        self.url = url
        self.content = content
        self.date = date
        self.author = author
        self.categories = categories or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "date": self.date,
            "author": self.author,
            "categories": self.categories
        }

async def extract_blog_posts(url: str, max_posts: int = 10) -> List[BlogPost]:
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    
    # Configure crawler
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=['form', 'header'],
        exclude_external_links=True,
        process_iframes=True,
        remove_overlay_elements=True,
    )
    
    posts = []
    
    # Create the crawler instance
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Crawl the URL
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        
        if not result.success:
            print(f"Failed to crawl: {{result.error_message}}")
            return posts
        
        # Extract blog post links
        # This is a generic implementation that needs to be customized for the specific website
        post_links = []
        for link in result.links["internal"]:
            href = link["href"]
            # Filter for blog post links (customize this for the specific website)
            if "/blog/" in href or "/post/" in href or "/article/" in href:
                post_links.append(href)
        
        # Limit the number of posts
        post_links = post_links[:max_posts]
        
        # Crawl each blog post
        for post_url in post_links:
            post_result = await crawler.arun(
                url=post_url,
                config=crawl_config
            )
            
            if not post_result.success:
                print(f"Failed to crawl post {{post_url}}: {{post_result.error_message}}")
                continue
            
            # Extract post information
            title = post_result.title
            content = post_result.markdown_v2.raw_markdown
            
            # Extract date and author (customize this for the specific website)
            date = None
            author = None
            categories = []
            
            # Example: Extract date from meta tags
            date_meta = post_result.soup.select_one('meta[property="article:published_time"]')
            if date_meta:
                date = date_meta["content"]
            
            # Example: Extract author from meta tags or content
            author_meta = post_result.soup.select_one('meta[name="author"]')
            if author_meta:
                author = author_meta["content"]
            
            # Example: Extract categories from meta tags or content
            category_elements = post_result.soup.select('.category')
            for element in category_elements:
                categories.append(element.text.strip())
            
            # Create a blog post object
            post = BlogPost(
                title=title,
                url=post_url,
                content=content,
                date=date,
                author=author,
                categories=categories
            )
            
            posts.append(post)
        
        return posts

async def save_blog_posts(posts: List[BlogPost], output_dir: str) -> None:
    \"\"\"
    Save blog posts as markdown files.
    
    Args:
        posts: List of blog posts
        output_dir: Output directory
    \"\"\"
    os.makedirs(output_dir, exist_ok=True)
    
    for i, post in enumerate(posts):
        # Create a filename from the title
        filename = f"{{i+1:02d}}-{{post.title.lower().replace(' ', '-')}}.md"
        filename = ''.join(c if c.isalnum() or c in '-_. ' else '-' for c in filename)
        filepath = os.path.join(output_dir, filename)
        
        # Create markdown content
        markdown = f"# {{post.title}}\\n\\n"
        
        if post.date:
            markdown += f"Date: {{post.date}}\\n\\n"
        
        if post.author:
            markdown += f"Author: {{post.author}}\\n\\n"
        
        if post.categories:
            markdown += f"Categories: {{', '.join(post.categories)}}\\n\\n"
        
        markdown += f"URL: {{post.url}}\\n\\n"
        markdown += post.content
        
        # Save to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        print(f"Saved blog post to {{filepath}}")
    
    # Save metadata to JSON
    metadata = {{
        "total_posts": len(posts),
        "crawled_at": datetime.now().isoformat(),
        "posts": [post.to_dict() for post in posts]
    }}
    
    with open(os.path.join(output_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata to {{os.path.join(output_dir, 'metadata.json')}}")

async def crawl_blog_website():
    # URL of the blog website
    url = "{url}"
    
    # Output directory for blog posts
    output_dir = "blog_posts"
    
    # Extract blog posts
    posts = await extract_blog_posts(url, max_posts=10)
    
    # Print the results
    print(f"Found {{len(posts)}} blog posts")
    for post in posts:
        print(f"- {{post.title}}")
    
    # Save blog posts
    await save_blog_posts(posts, output_dir)
    
    print(f"Completed crawling {{len(posts)}} blog posts")

# Run the crawler
if __name__ == "__main__":
    asyncio.run(crawl_blog_website())
""".format(url=analysis["root_url"])
        
        return code


# Import GitHub strategy
from .github_strategy import GitHubDocumentationStrategy

# Factory function to create the appropriate strategy
def create_strategy(website_type: str, url: str = None) -> ScrapingStrategy:
    """
    Create a scraping strategy based on the website type and URL.
    
    Args:
        website_type: The type of website (e.g., "ecommerce", "documentation", "blog", "github")
        url: The URL of the website (optional)
        
    Returns:
        A scraping strategy instance
    """
    # Check if this is a GitHub URL and the website type is documentation
    if url and website_type.lower() == "documentation":
        parsed = urlparse(url)
        if parsed.netloc == "github.com" or parsed.netloc.endswith(".github.com"):
            return GitHubDocumentationStrategy()
    
    strategies = {
        "ecommerce": EcommerceStrategy,
        "documentation": DocumentationStrategy,
        "blog": BlogStrategy,
        "github": GitHubDocumentationStrategy,
        "generic": GenericStrategy
    }
    
    strategy_class = strategies.get(website_type.lower(), GenericStrategy)
    return strategy_class()
