# Technical Context: crawl4ai-rag

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary development language
- **crawl4ai**: Foundation library for web crawling capabilities
- **Supabase**: Database for storing crawled pages and embeddings
- **PostgreSQL**: Underlying database technology used by Supabase
- **OpenAI Embeddings**: For generating vector embeddings of crawled content
- **LangChain**: For RAG (Retrieval-Augmented Generation) capabilities
- **MCP Servers**: For enhanced API access and content retrieval
  - **GitHub MCP Server**: For structured GitHub repository access
  - **Fetch MCP Server**: For web content retrieval and parsing
  - **Subprocess Communication**: For reliable interaction with MCP servers via stdin/stdout

### Key Libraries
- **requests/httpx**: For HTTP requests
- **BeautifulSoup4**: For HTML parsing
- **pgvector**: For vector similarity search in PostgreSQL
- **pydantic**: For data validation and settings management
- **pytest**: For testing infrastructure
- **loguru**: For enhanced logging capabilities
- **typer/click**: For CLI interface
- **jinja2**: For code template generation
- **modelcontextprotocol**: For MCP server integration
- **subprocess**: For managing MCP server subprocesses
- **json**: For serializing/deserializing MCP server requests and responses

## Development Environment

### Setup Requirements
- Python 3.9 or higher
- Poetry or pip for dependency management
- Supabase account and project
- OpenAI API key for embeddings generation
- Git for version control

### Environment Variables
```
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
OPENAI_API_KEY=your-openai-api-key
LOG_LEVEL=INFO
GITHUB_TOKEN=your-github-token  # For GitHub MCP server authentication
```

### Environment Variable Security
- **File-Based Configuration**: Environment variables are loaded from a `.env` file using pydantic_settings
- **Template Approach**: `.env.example` serves as a template with placeholder values
- **Verification Process**:
  ```bash
  # Check if .env file exists
  ls -Force .env
  
  # Verify .env is not tracked in git
  git check-ignore .env
  
  # Audit git history to ensure .env was never committed
  git log -- .env
  ```
- **Permissions**: Set restricted permissions on the `.env` file to prevent unauthorized access
- **Validation**: Environment variables are validated at startup with clear error messages for missing values
- **Documentation**: Required variables are documented in `.env.example` with descriptions

### Development Workflow
1. Clone repository
2. Install dependencies using uv (preferred), Poetry, or pip
3. Set up environment variables
4. Run tests to verify setup
5. Start development

### Dependency Management
- Use uv for dependency management (preferred)
- Install packages with `uv pip install <package>`
- Install project in development mode with `uv pip install -e .`
- For packages with binary components (like Playwright), follow up with additional installation steps:
  - Example: `python -m playwright install` after installing playwright
- When adding new dependencies, update pyproject.toml

## Database Schema

The project uses the `crawl4ai_site_pages` table in Supabase with the following schema:

```sql
CREATE TABLE crawl4ai_site_pages (
    url TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embeddings VECTOR(1536),  -- For OpenAI embeddings
    last_crawled TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    title TEXT,
    description TEXT,
    status INTEGER DEFAULT 200
);

-- Index for vector similarity search
CREATE INDEX ON crawl4ai_site_pages USING ivfflat (embeddings vector_cosine_ops);
```

## API Design

### Core Functions

```python
# Main entry point
def analyze_and_generate(
    urls: List[str],
    purpose: str,
    output_code: bool = True,
    output_markdown: bool = False,
    markdown_output_dir: Optional[str] = None,
    use_mcp: bool = True
) -> Dict[str, Union[str, List[str]]]:
    """
    Analyze websites and generate code/markdown based on purpose.
    
    Args:
        urls: List of URLs to analyze
        purpose: Description of scraping purpose
        output_code: Whether to return generated code
        output_markdown: Whether to generate markdown
        markdown_output_dir: Directory to write markdown files (if None, returns content)
        use_mcp: Whether to use MCP servers for content retrieval
        
    Returns:
        Dictionary containing generated code and/or paths to markdown files
    """
    pass

# Database synchronization
def sync_website_to_supabase(
    url: str,
    max_depth: int = 2,
    force_update: bool = False,
    use_mcp: bool = True
) -> int:
    """
    Crawl website and sync pages to Supabase.
    
    Args:
        url: Root URL to crawl
        max_depth: Maximum crawl depth
        force_update: Whether to update existing pages
        use_mcp: Whether to use MCP servers for content retrieval
        
    Returns:
        Number of pages synced
    """
    pass

# GitHub repository synchronization
def sync_github_repository(
    owner: str,
    repo: str,
    branch: str = "main",
    include_issues: bool = False,
    include_pull_requests: bool = False
) -> int:
    """
    Sync GitHub repository content to Supabase using MCP.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        branch: Branch to sync (default: main)
        include_issues: Whether to include issues
        include_pull_requests: Whether to include pull requests
        
    Returns:
        Number of pages synced
    """
    pass
```

### CLI Interface

```
# Analyze and generate code
crawl4ai-rag analyze --url https://example.com --purpose "Extract all product information" --output-code

# Generate markdown
crawl4ai-rag analyze --url https://example.com --purpose "Convert documentation to markdown" --output-markdown --output-dir ./docs

# Sync website to Supabase
crawl4ai-rag sync --url https://example.com --depth 3

# Sync GitHub repository to Supabase
crawl4ai-rag sync-github --owner username --repo repository --branch main --include-issues
```

## Technical Constraints

### Performance Considerations
- Crawling large websites can be time-consuming
- Vector embeddings generation requires API calls to OpenAI
- Supabase has query limits that need to be managed
- Memory usage can be high when processing large websites
- MCP server requests have their own rate limits and quotas
- GitHub API (via MCP) has rate limiting that needs to be respected
- Subprocess-based MCP communication adds overhead for process creation and management
- Long-running MCP server subprocesses need proper cleanup to avoid resource leaks

### Security Considerations
- API keys need to be securely managed
- Crawled content may contain sensitive information
- Rate limiting and respectful crawling practices must be followed
- User-provided URLs must be validated and sanitized
- GitHub tokens require appropriate scopes for repository access
- MCP server authentication must be properly configured
- Subprocess commands must be validated to prevent command injection
- MCP server subprocess input/output must be properly sanitized
- Proper error handling for subprocess communication failures

### Scalability Considerations
- Supabase table size limits
- OpenAI API rate limits
- Concurrent crawling capabilities
- Memory usage for large websites

## Testing Strategy

### Unit Tests
- Test individual components (analyzer, code generator, markdown generator)
- Mock external dependencies (Supabase, OpenAI, HTTP requests)
- Validate output formats and error handling

### Integration Tests
- Test end-to-end workflows with controlled test websites
- Verify Supabase integration with a test database
- Test CLI interface functionality

### Mocking Strategy
- Use VCR or similar for HTTP request recording/playback
- Create fixture data for website content
- Mock Supabase responses for predictable testing
- Mock MCP server responses for GitHub and Fetch operations

## Deployment Considerations

### Package Distribution
- Published to PyPI for easy installation
- Docker container for consistent environment
- Clear documentation for setup and configuration

### Dependencies Management
- Pinned versions for stability
- Minimal production dependencies
- Optional dependencies for development

### Monitoring and Logging
- Structured logging with loguru
- Error tracking and reporting
- Performance metrics collection
