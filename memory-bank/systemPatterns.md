# System Patterns: crawl4ai-rag

## System Architecture

The crawl4ai-rag system follows a modular architecture organized around core capabilities, now enhanced with MCP integration:

```mermaid
flowchart TD
    User([User]) -->|Provides URLs & Purpose| Input[Input Handler]
    Input --> Analyzer[Website Analyzer]
    
    Analyzer --> MCP[MCP Integration]
    MCP --> SubprocessMgr[Subprocess Manager]
    SubprocessMgr -->|stdin/stdout| GithubMCP[GitHub MCP Server]
    SubprocessMgr -->|stdin/stdout| FetchMCP[Fetch MCP Server]
    
    Analyzer --> DB[(Supabase DB)]
    Analyzer --> CodeGen[Code Generator]
    Analyzer --> MarkdownGen[Markdown Generator]
    
    GithubMCP --> SubprocessMgr
    FetchMCP --> SubprocessMgr
    SubprocessMgr --> MCP
    
    CodeGen --> Output[Output Handler]
    MarkdownGen --> Output
    Output -->|Returns Code/Markdown| User
    
    subgraph "Data Persistence"
        DB
    end
    
    subgraph "Core Processing"
        Analyzer
        CodeGen
        MarkdownGen
    end
    
    subgraph "MCP Services"
        MCP
        SubprocessMgr
        GithubMCP
        FetchMCP
    end
```

## Key Components

### 1. Input Handler
- Processes user requests for website analysis
- Validates URLs and scraping purpose
- Configures output preferences (code, markdown, or both)

### 2. Website Analyzer
- Analyzes websites to understand structure
- Identifies key elements based on scraping purpose
- Builds internal representation of website structure
- Interfaces with Supabase for storing and retrieving crawled pages
- Coordinates with MCP servers for specialized content retrieval

### 3. MCP Integration
- Leverages Model Context Protocol servers for enhanced capabilities:
  - **GitHub MCP Server**: Provides structured access to GitHub repositories
  - **Fetch MCP Server**: Handles web content retrieval with built-in parsing
- Manages authentication and request handling for MCP services
- Provides fallback mechanisms when MCP services are unavailable
- Uses subprocess-based communication for reliable interaction with MCP servers:
  - **Subprocess Manager**: Handles stdin/stdout communication with MCP servers
  - **Service Layer**: Provides a consistent interface to MCP server capabilities
  - **Error Handling**: Implements retry logic and graceful degradation

### 3. Code Generator
- Transforms website analysis into Python code
- Tailors code to specific scraping requirements
- Includes error handling and documentation in generated code
- Optimizes code for efficiency and readability

### 4. Markdown Generator
- Processes scraped content into structured markdown
- Organizes content based on website hierarchy
- Preserves important formatting and relationships
- Handles various content types (text, tables, lists, etc.)

### 5. Output Handler
- Manages delivery of generated code and/or markdown
- Supports direct return or file writing options
- Handles error reporting and status updates

### 6. Supabase Integration
- Stores crawled pages for efficient retrieval
- Maintains embeddings for semantic search
- Tracks crawl history and updates
- Provides persistence across sessions

## Design Patterns

### Command Pattern
Used for encapsulating scraping requests with all necessary parameters and execution logic.

```python
class ScrapingCommand:
    def __init__(self, urls, purpose, output_preferences):
        self.urls = urls
        self.purpose = purpose
        self.output_preferences = output_preferences
        
    def execute(self):
        # Orchestrate the scraping process
        pass
```

### Strategy Pattern
Applied for different scraping strategies based on website type and purpose.

```python
class ScrapingStrategy:
    def scrape(self, url, purpose):
        pass
        
class EcommerceScraper(ScrapingStrategy):
    def scrape(self, url, purpose):
        # E-commerce specific scraping logic
        pass
        
class DocumentationScraper(ScrapingStrategy):
    def scrape(self, url, purpose):
        # Documentation specific scraping logic
        pass
```

### Factory Pattern
Used for creating appropriate code generators based on scraping requirements.

```python
class CodeGeneratorFactory:
    @staticmethod
    def create_generator(website_type, scraping_purpose):
        if website_type == "ecommerce":
            return EcommerceCodeGenerator()
        elif website_type == "documentation":
            return DocumentationCodeGenerator()
        # ...
```

### Repository Pattern
Applied for database interactions with Supabase.

```python
class PageRepository:
    def __init__(self, supabase_client):
        self.client = supabase_client
        
    def save_page(self, url, content, embeddings):
        # Save page to Supabase
        pass
        
    def get_page(self, url):
        # Retrieve page from Supabase
        pass
        
    def update_page(self, url, content, embeddings):
        # Update existing page
        pass
```

### Adapter Pattern
Used for integrating MCP services with the core system.

```python
class McpAdapter:
    def __init__(self, server_name):
        self.server_name = server_name
        
    async def fetch_content(self, url, **options):
        # Use appropriate MCP tool based on URL and server
        pass
        
class GithubMcpAdapter(McpAdapter):
    async def fetch_repository(self, owner, repo):
        # Use github MCP server to fetch repository data
        pass
        
    async def fetch_file_contents(self, owner, repo, path, branch="main"):
        # Use github MCP server to fetch file contents
        pass
```

### Subprocess Communication Pattern
Used for reliable communication with MCP servers via stdin/stdout.

```python
class SubprocessManager:
    def __init__(self, server_cmd):
        self.server_cmd = server_cmd
        self.process = None
        
    def start_server(self):
        # Start the MCP server subprocess
        self.process = subprocess.Popen(
            self.server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
    def send_request(self, request):
        # Send JSON request and get response
        json_request = json.dumps(request) + "\n"
        self.process.stdin.write(json_request)
        self.process.stdin.flush()
        
        # Read response
        response_line = self.process.stdout.readline()
        return json.loads(response_line)
        
    def stop_server(self):
        # Terminate the server process
        if self.process:
            self.process.terminate()
```

### Service Pattern
Used for providing a consistent interface to MCP servers.

```python
class GitHubMcpService:
    def __init__(self):
        self.manager = SubprocessManager([
            "cmd.exe", "/c", 
            "npx", "-y", "@modelcontextprotocol/server-github"
        ])
        self.manager.start_server()
        
    async def search_repositories(self, query, page=1, per_page=30):
        # Use the subprocess manager to call the GitHub MCP
        result = self.manager.send_request({
            "server_name": "github.com/modelcontextprotocol/servers/tree/main/src/github",
            "tool_name": "search_repositories",
            "arguments": {
                "query": query,
                "page": page,
                "perPage": per_page
            }
        })
        return result
```

## Data Flow

1. **Input Processing**:
   - User provides URLs and scraping purpose
   - System validates input and configures processing

2. **Content Retrieval**:
   - System checks Supabase for existing data
   - For GitHub URLs, uses GitHub MCP server to fetch repository data
   - For web content, uses Fetch MCP server or falls back to direct crawling
   - Stores retrieved content in Supabase

3. **Website Analysis**:
   - Analyzes content based on scraping purpose
   - Identifies key elements and structure
   - Generates metadata and embeddings

4. **Generation Phase**:
   - Creates Python code for the specific scraping task
   - Optionally processes content into markdown

5. **Output Delivery**:
   - Returns generated code to user
   - Optionally writes markdown to specified location
   - Provides status and any error information

## Error Handling Strategy

- **Graceful Degradation**: System attempts to provide partial results when possible
- **Detailed Reporting**: Clear error messages with context and suggestions
- **Retry Mechanisms**: Automatic retries for transient failures
- **Validation Checks**: Input validation to prevent common errors
- **Logging**: Comprehensive logging for debugging and improvement

## Environment Variable Handling

The system uses a structured approach to environment variable management:

```mermaid
flowchart TD
    A[Application Start] --> B{.env File Exists?}
    B -->|Yes| C[Load Variables from .env]
    B -->|No| D[Check Environment Variables]
    C --> E[Validate Required Variables]
    D --> E
    E -->|Missing Variables| F[Raise Configuration Error]
    E -->|All Variables Present| G[Initialize Components]
    F --> H[Log Detailed Error]
    H --> I[Exit with Clear Message]
    G --> J[Application Running]
    
    subgraph "Security Checks"
        K[Periodic Audit]
        L[Permission Verification]
        M[Git History Check]
    end
    
    J --> K
    K --> L
    L --> M
```

The environment variable loading process is handled by pydantic_settings with the following key features:
1. **Centralized Configuration**: All environment variables are defined in the `Settings` class in `config.py`
2. **Validation**: Type checking and required field validation through Pydantic
3. **Default Values**: Sensible defaults where appropriate
4. **Documentation**: Clear documentation of required variables in `.env.example`
5. **Error Handling**: Descriptive error messages when required variables are missing

## Extension Points

The system is designed with several extension points:

1. **New Website Types**: Add specialized analyzers for specific website categories
2. **Custom Code Templates**: Extend code generation with new templates
3. **Output Formats**: Add support for formats beyond code and markdown
4. **Scraping Strategies**: Implement new strategies for different scraping purposes
5. **Database Providers**: Extend beyond Supabase to other storage solutions
6. **MCP Integrations**: Add support for additional MCP servers and capabilities
7. **Content Processors**: Implement specialized processors for different content types
