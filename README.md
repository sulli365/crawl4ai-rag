# Crawl4AI RAG

An agentic RAG (Retrieval-Augmented Generation) application built around the crawl4ai Python library. The application serves as an intelligent assistant that can analyze websites, generate scraping code, and produce structured markdown documentation based on the scraped content.

## Features

- **Website Analysis**: Intelligently analyze websites to understand their structure and content organization
- **Code Generation**: Produce Python code tailored to specific scraping requirements
- **Markdown Export**: Convert scraped content into well-structured markdown files
- **Flexible Output Options**: Return content directly or write to files based on user preference
- **Supabase Integration**: Store and retrieve crawled pages using Supabase for persistence
- **Automatic Updates**: Monitor source websites for changes and update the database accordingly

## Setup

1. Install dependencies:
```bash
pip install -e .
```

2. Configure environment variables:
- Copy `.env.example` to `.env` (or set environment variables)
- Add your API keys:
  ```
  SUPABASE_URL=your-supabase-url
  SUPABASE_KEY=your-supabase-key
  OPENAI_API_KEY=your-openai-api-key
  GITHUB_TOKEN=your-github-token (optional)
  ```

## Usage

### Command Line Interface

#### Analyze a website and generate code

```bash
crawl4ai-rag analyze https://example.com --purpose "Extract all product information"
```

#### Generate markdown from a website

```bash
crawl4ai-rag analyze https://example.com --purpose "Convert documentation to markdown" --output-markdown --output-dir ./docs
```

#### Sync crawl4ai GitHub repository and documentation to Supabase

```bash
crawl4ai-rag sync
```

#### Detect website type

```bash
crawl4ai-rag detect https://example.com
```

### Python API

```python
import asyncio
from crawl4ai_rag import analyze_and_generate

async def main():
    # Analyze website and generate code
    result = await analyze_and_generate(
        urls="https://example.com",
        purpose="Extract all product information",
        output_code=True,
        output_markdown=True,
        markdown_output_dir="./docs"
    )
    
    # Print generated code
    print(result["code"])
    
    # Print markdown files
    print(result["markdown_files"])

# Run the async function
asyncio.run(main())
```

## Project Structure

```
crawl4ai-rag/
│── analyzer/            # Website analysis components
│   │── strategies/      # Scraping strategies for different website types
│── codegen/             # Code generation components
│   │── templates/       # Code templates
│── crawlers/            # Crawlers for different sources
│   │── docs/            # Documentation website crawler
│   │── github/          # GitHub repository crawler
│── exporters/           # Export components
│── supabase/            # Supabase integration
│── utils/               # Utility functions
│── cli.py               # Command-line interface
│── config.py            # Configuration settings
│── pyproject.toml       # Project metadata and dependencies
│── README.md            # This file
```

## Development

### Requirements

- Python 3.9 or higher
- Supabase account and project
- OpenAI API key

### Testing

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Type Checking

```bash
mypy .
```

## License

MIT
