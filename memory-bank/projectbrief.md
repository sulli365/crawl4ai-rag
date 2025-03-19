# Project Brief: crawl4ai-rag

## Project Overview
crawl4ai-rag is an agentic RAG (Retrieval-Augmented Generation) application built around the crawl4ai Python library. The application serves as an intelligent assistant that can analyze websites, generate scraping code, and produce structured markdown documentation based on the scraped content.

## Core Objectives
1. Analyze website structure when provided with URL(s) and a scraping purpose
2. Generate and return Python code for accomplishing the specified scraping task
3. Process and structure the scraped content into markdown files
4. Provide options for direct content return or file writing to specified locations
5. Maintain a Supabase database of crawled pages for efficient retrieval and analysis

## Key Features
- **Website Structure Analysis**: Intelligently analyze websites to understand their structure and content organization
- **Code Generation**: Produce Python code tailored to specific scraping requirements
- **Markdown Export**: Convert scraped content into well-structured markdown files
- **Flexible Output Options**: Return content directly or write to files based on user preference
- **Supabase Integration**: Store and retrieve crawled pages using Supabase for persistence
- **Automatic Updates**: Monitor source websites for changes and update the database accordingly

## Technical Requirements
- Python package structure for easy import and use in other projects
- Supabase database integration following the crawl4ai_site_pages schema
- Error logging and testing infrastructure
- Documentation for usage and extension

## Success Criteria
- Successfully analyze websites and generate working scraping code
- Produce well-structured markdown files from scraped content
- Maintain an up-to-date database of crawled pages
- Provide a clean, well-documented API for integration into other projects
- Include comprehensive error handling and testing

## Non-Goals
- Creating a web interface or GUI
- Supporting non-Python environments
- Implementing an MCP server (as originally planned)
- Building a general-purpose web crawler
