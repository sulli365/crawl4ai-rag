# Remaining GitHub MCP Integration Edits

This document outlines the files that still need to be edited to complete the GitHub MCP integration using the subprocess approach.

## Files to Edit

1. **analyzer/github_mcp.py**
   - Already updated to use GitHubMcpService with the subprocess approach

2. **analyzer/github_mcp_service.py**
   - Already updated to use SubprocessManager for communication with the GitHub MCP server

3. **utils/mcp_subprocess.py**
   - Already implemented to handle subprocess communication with MCP servers

4. **analyzer/strategies/github_strategy.py**
   - Already updated to use GitHubMcpService instead of McpClient

5. **codegen/templates/github_docs_scraper.j2**
   - Already updated to use GitHubMcpService instead of McpClient

6. **test_github_mcp.py**
   - Already updated to test the GitHub MCP integration

## Files That May Need Review

1. **utils/mcp_client.py**
   - This file may need to be removed or updated to use the new subprocess approach if there are any remaining references to it in the codebase.

2. **cli.py**
   - Verify that the CLI commands for GitHub repository syncing are using the new GitHubMcpService.

3. **config.py**
   - Ensure that the GitHub configuration options are properly set up for the MCP integration.

## Implementation Status

The GitHub MCP integration using the subprocess approach has been successfully implemented. The key components are:

1. **SubprocessManager** in `utils/mcp_subprocess.py` - Handles communication with MCP servers via stdin/stdout
2. **GitHubMcpService** in `analyzer/github_mcp_service.py` - Provides a service interface for GitHub MCP operations
3. **GitHubMcpScraper** in `analyzer/github_mcp.py` - Implements repository syncing using the GitHubMcpService
4. **GitHubDocumentationStrategy** in `analyzer/strategies/github_strategy.py` - Uses GitHubMcpService for GitHub documentation analysis
5. **GitHub documentation scraper template** in `codegen/templates/github_docs_scraper.j2` - Uses GitHubMcpService for code generation

All of these components have been updated to use the subprocess approach for communication with the GitHub MCP server, as described in `calling-github-mcp.txt`.

## Next Steps

1. Test the GitHub MCP integration with the crawl4ai repository
2. Verify that all components are working correctly
3. Update the memory banks with the latest changes
4. Document the GitHub MCP integration in the project documentation
