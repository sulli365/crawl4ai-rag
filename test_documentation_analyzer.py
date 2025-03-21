"""
Test script for the documentation analyzer and validation features.

This script demonstrates how to use the enhanced website analyzer
to analyze documentation pages and validate their structure.
"""

import asyncio
import json
from pprint import pprint

from analyzer.website_analyzer import website_analyzer
from utils.validation import validate_documentation_structure, validate_code_blocks


async def test_documentation_analysis(url: str):
    """
    Test the documentation analysis features on a given URL.
    
    Args:
        url: The URL of a documentation page to analyze
    """
    print(f"\n\n{'='*80}")
    print(f"Analyzing documentation at: {url}")
    print(f"{'='*80}\n")
    
    # Analyze the URL
    result = await website_analyzer.analyze_url(url, extract_text=True, extract_links=True)
    
    if "error" in result:
        print(f"Error analyzing URL: {result['error']}")
        return
    
    # Print basic information
    print(f"Title: {result['title']}")
    print(f"Word count: {result['structure']['word_count']}")
    print(f"Reading time: {result['structure']['reading_time_minutes']} minutes")
    print(f"Code blocks: {result['structure']['code_blocks']}")
    print(f"Link count: {result['structure']['link_count']}")
    
    # Print documentation-specific metrics
    print("\nDocumentation Metrics:")
    print(f"API sections: {len(result['structure']['api_sections'])}")
    print(f"Example count: {result['structure']['example_count']}")
    print(f"Parameter tables: {result['structure']['parameter_tables']}")
    print(f"Has installation section: {result['structure']['has_installation_section']}")
    print(f"Has usage section: {result['structure']['has_usage_section']}")
    print(f"Has API reference: {result['structure']['has_api_reference']}")
    
    # Print code block analysis
    print("\nCode Block Analysis:")
    code_blocks = result['structure']['code_block_types']
    print(f"Total code blocks: {code_blocks['total']}")
    print("By language:")
    for lang, count in code_blocks['by_language'].items():
        print(f"  - {lang}: {count}")
    print("By purpose:")
    for purpose, count in code_blocks['by_purpose'].items():
        print(f"  - {purpose}: {count}")
    
    # Print validation results if available
    if "validation" in result and "documentation" in result["validation"]:
        print("\nDocumentation Validation:")
        validation = result["validation"]["documentation"]
        print(f"Is valid: {validation['is_valid']}")
        print(f"Score: {validation['score']}/{validation['max_score']} ({validation['percentage']}%)")
        
        if validation["errors"]:
            print("\nErrors:")
            for error in validation["errors"]:
                print(f"  - {error['message']} (Code: {error['code']})")
        
        if validation["warnings"]:
            print("\nWarnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning['message']} (Code: {warning['code']})")
    
    # Print code block validation if available
    if "validation" in result and "code_blocks" in result["validation"]:
        print("\nCode Block Validation:")
        validation = result["validation"]["code_blocks"]
        print(f"Is valid: {validation['is_valid']}")
        print(f"Score: {validation['score']}/{validation['max_score']} ({validation['percentage']}%)")
        
        if validation["warnings"]:
            print("\nWarnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning['message']} (Code: {warning['code']})")


async def test_website_documentation_analysis(url: str, max_urls: int = 5):
    """
    Test the website-wide documentation analysis features on a given URL.
    
    Args:
        url: The root URL of a website to analyze
        max_urls: Maximum number of URLs to analyze
    """
    print(f"\n\n{'='*80}")
    print(f"Analyzing website documentation at: {url}")
    print(f"{'='*80}\n")
    
    # Analyze the website
    result = await website_analyzer.analyze_website(url, max_depth=1, max_urls=max_urls, extract_text=True, extract_links=True)
    
    if "error" in result:
        print(f"Error analyzing website: {result['error']}")
        return
    
    # Print basic information
    print(f"Title: {result['title']}")
    print(f"Total pages: {result['structure']['total_pages']}")
    print(f"Total internal links: {result['structure']['total_internal_links']}")
    print(f"Total external links: {result['structure']['total_external_links']}")
    
    # Print documentation pages
    if "documentation_pages" in result["structure"]:
        doc_pages = result["structure"]["documentation_pages"]
        print(f"\nDocumentation Pages: {len(doc_pages)}")
        for i, page in enumerate(doc_pages, 1):
            print(f"{i}. {page['title']} - {page['url']}")
    
    # Print documentation analysis
    if "documentation_analysis" in result["structure"]:
        analysis = result["structure"]["documentation_analysis"]
        print("\nDocumentation Analysis:")
        print(f"Total documentation pages: {analysis['total_pages']}")
        print(f"Valid documentation pages: {analysis['valid_pages']}")
        print(f"Overall score: {analysis['overall_score']}/{analysis['overall_max_score']} ({analysis['overall_percentage']}%)")
        print(f"Completeness level: {analysis['completeness_level']}")
        
        if analysis["gaps"]:
            print("\nDocumentation Gaps:")
            for gap in analysis["gaps"]:
                print(f"  - {gap}")
        
        if analysis["errors"]:
            print("\nErrors:")
            for error in analysis["errors"]:
                print(f"  - {error['message']} (URL: {error['url']})")
        
        if analysis["warnings"]:
            print("\nWarnings:")
            for warning in analysis["warnings"]:
                print(f"  - {warning['message']} (URL: {warning['url']})")


async def main():
    """Run the documentation analyzer tests."""
    # Test single documentation page analysis
    await test_documentation_analysis("https://docs.python.org/3/library/asyncio.html")
    
    # Test website-wide documentation analysis
    await test_website_documentation_analysis("https://docs.python.org/3/", max_urls=5)


if __name__ == "__main__":
    asyncio.run(main())
