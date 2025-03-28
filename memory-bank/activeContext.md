# Active Context: crawl4ai-rag

## Current Focus
The project has been restructured from an MCP server to an agentic RAG application focused on website analysis, code generation, and markdown export. The initial implementation of the core architecture and components has been completed. Currently, we are focusing on enhancing the website analyzer with documentation-specific metrics and validation, improving error handling with custom exceptions, and preparing for code generation template enhancements. We have also implemented a GitHub-specific documentation scraper to better handle GitHub repositories. We've resolved import issues by restructuring the local supabase module to db_client to avoid conflicts with the external Supabase package, and installed Playwright for web crawling capabilities. We have now successfully implemented the GitHub MCP integration for retrieving repository content and storing it in Supabase, with enhanced configuration options and CLI improvements. We are currently working on improving the GitHub MCP integration to use a subprocess approach for more reliable communication with the GitHub MCP server, but are encountering some challenges with the subprocess communication.

## Recent Changes
- Enhanced the website analyzer with documentation-specific metrics:
  - Added API section detection
  - Implemented code block analysis by language and purpose
  - Added parameter table detection
  - Added documentation section identification
- Implemented documentation validation framework:
  - Created DocumentationError class hierarchy
  - Added validation for documentation structure
  - Added validation for code blocks
  - Implemented website-wide documentation analysis
- Improved error handling with custom exceptions and severity levels
- Added heuristic detection of documentation pages
- Implemented MCP integration for GitHub scraping:
  - Created MCP client utilities for interacting with MCP servers
  - Implemented GitHub MCP scraper for retrieving repository content
  - Updated GitHubDocumentationStrategy to use MCP for enhanced analysis
  - Modified GitHub documentation scraper template to support MCP
  - Added CLI command for syncing GitHub repositories to Supabase
  - Implemented fallback mechanisms for when MCP is unavailable
- Enhanced GitHub MCP integration:
  - Added GitHubConfig class with configurable options
  - Implemented file filtering based on extensions and patterns
  - Updated CLI to support multiple repositories
  - Added direct communication with GitHub MCP server
  - Improved error handling for MCP server interactions
  - Implemented subprocess-based approach for more reliable communication
  - Added retry logic for transient failures
  - Created test script for verification
  - Implemented SubprocessManager for MCP server communication
  - Updated GitHubMcpService to use subprocess approach
- Updated dependencies:
  - Added pydantic-settings to support newer Pydantic versions
  - Fixed import issues in utils/logging.py

## Current Tasks
1. **Website Analyzer Enhancement**
   - ✅ Added documentation-specific metrics to structure analysis
   - ✅ Implemented API section detection
   - ✅ Added code block analysis by language and purpose
   - ✅ Added documentation validation framework
   - ✅ Implemented website-wide documentation analysis

2. **Error Handling Enhancement**
   - ✅ Created DocumentationError class hierarchy
   - ✅ Implemented severity levels for validation errors
   - ✅ Added structured error reporting
   - ⏳ Implement additional custom exceptions for other components

3. **Code Generation Template Enhancement**
   - ✅ Created GitHub-specific documentation scraper template
   - ✅ Added GitHub documentation strategy
   - ✅ Updated CLI with GitHub-specific command
   - ⏳ Add error handling blocks to generated code
   - ⏳ Implement metadata tracking in generated code

4. **Testing Infrastructure**
   - ⏳ Set up testing infrastructure
   - ⏳ Create basic tests for core components
   - ⏳ Establish CI/CD workflow

5. **Dependency Management**
   - ✅ Updated dependencies to support newer Pydantic versions
   - ✅ Fixed import issues in utils/logging.py
   - ⏳ Ensure all required dependencies are properly installed

## Next Steps
1. ✅ Enhance website analyzer with documentation-specific metrics
2. ✅ Implement documentation validation framework
3. ✅ Add website-wide documentation analysis
4. ✅ Create specialized templates for GitHub documentation
5. ✅ Implement MCP-powered GitHub scraper:
   - ✅ Migrate API calls to github.com/modelcontextprotocol/servers tools
   - ✅ Configure MCP server authentication
   - ✅ Update error handling for MCP integration
6. ⏳ Enhance error handling in other components:
   - Add custom exceptions for code generation
   - Add custom exceptions for markdown export
   - Implement retry logic for transient failures
7. ⏳ Implement testing infrastructure:
   - Create test directory structure
   - Establish base test classes
   - Implement VCR.py configuration for HTTP mocking
8. ⏳ Improve Supabase integration:
   - Implement connection pooling
   - Add retry logic for repository methods
   - Enhance error recovery for Supabase disconnects
9. ⏳ Resolve dependency issues:
   - Ensure all required packages are properly installed
   - Fix any import or compatibility issues

## Active Decisions

### Documentation Analysis Approach
We've implemented a comprehensive approach to documentation analysis:

1. **Detection Phase**: Identify if a page is likely documentation based on:
   - Title keywords (docs, reference, guide, etc.)
   - Content indicators (installation sections, API references, etc.)
   - Structural elements (code blocks, parameter tables, etc.)

2. **Analysis Phase**: Extract metrics about the documentation:
   - API section detection with start/end lines
   - Code block analysis by language and purpose
   - Parameter table detection
   - Section identification (installation, usage, API reference)

3. **Validation Phase**: Validate documentation quality:
   - Structure validation (headings, sections, etc.)
   - Code block validation (languages, purposes, etc.)
   - Error reporting with severity levels
   - Score calculation for overall quality

4. **Website-wide Analysis**: Aggregate documentation metrics across pages:
   - Identify all documentation pages
   - Calculate overall documentation quality
   - Identify gaps in documentation
   - Provide recommendations for improvement

### Error Handling Strategy
We've enhanced the error handling strategy with a more structured approach:

1. **Custom Exception Hierarchy**:
   - Base `DocumentationError` class
   - Severity levels (WARNING, ERROR, CRITICAL)
   - Error codes for specific validation issues
   - Detailed error messages with context

2. **Validation Results Structure**:
   - Clear separation of errors and warnings
   - Scoring system for documentation quality
   - Percentage-based quality assessment
   - Gap identification for improvement recommendations

3. **Graceful Degradation**:
   - Continue analysis even with partial validation failures
   - Provide as much useful information as possible
   - Clearly indicate which validations failed and why
   - Suggest improvements for failed validations

## Open Questions
1. How to efficiently test the documentation validation capabilities?
2. What additional documentation metrics would be valuable to extract?
3. How to handle documentation with non-standard formats?
4. What specialized code templates should be created for different documentation styles?
5. How to optimize the performance of the documentation analyzer for large documentation sites?
6. How to handle multilingual documentation?
7. What additional validation rules should be implemented for different types of documentation?

## Current Blockers
- Need to implement testing for the new documentation validation features
- Need to implement testing for the GitHub MCP integration
- Need to resolve dependency issues with crawl4ai and other packages
- Need to improve Supabase integration with connection pooling and retry logic
- Need to ensure proper environment variable handling:
  - Create a proper .env file from .env.example
  - Verify environment variables are loaded correctly
  - Implement security checks for .env file
  - Add validation for required environment variables

## Security Audit Status
- Added comprehensive environment variable security documentation
- Updated .clinerules with detailed security practices for API keys and environment variables
- Added environment variable loading flowchart to systemPatterns.md
- Enhanced techContext.md with hidden file security patterns
- Pending implementation of automated environment variable validation checks
- Pending implementation of security audit scripts for .env file

## Recent Insights
- Documentation analysis requires a multi-faceted approach combining heuristics and pattern matching
- Validation should be flexible with different severity levels to accommodate various documentation styles
- Website-wide documentation analysis provides valuable insights beyond individual page analysis
- Code block analysis by language and purpose helps generate more targeted scraping code
- API section detection enables more precise extraction of API documentation
- Documentation quality can be quantified through a scoring system
- MCP integration provides a more robust and structured way to access GitHub repositories
- Fallback mechanisms are essential for ensuring system reliability when external services are unavailable
- Mock responses can be used for testing when MCP servers are not available
- Subprocess-based communication with MCP servers is more reliable than HTTP-based approaches
- Proper error handling and retry logic are essential for robust MCP server communication
- Standardizing the MCP server communication approach across the codebase improves maintainability
