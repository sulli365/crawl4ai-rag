"""
Configuration settings for the crawl4ai-rag application.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class GitHubConfig(BaseSettings):
    """
    GitHub-specific configuration settings.
    """
    mcp_server: str = Field(
        default="github.com/modelcontextprotocol/servers/tree/main/src/github",
        description="MCP server endpoint for GitHub operations"
    )
    target_repos: list = Field(
        default=["modelcontextprotocol/crawl4ai"],
        description="List of repos in 'owner/repo' format. Empty list enables custom input"
    )
    file_extensions: list = [".py", ".md", ".ipynb", ".rst"]
    exclude_paths: list = Field(
        default=["tests/"],
        description="Paths to exclude from crawling"
    )
    include_patterns: list = Field(
        default=["README.*", "examples/", "docs/"],
        description="Patterns that trigger inclusion regardless of extension"
    )

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Supabase settings
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    
    # OpenAI settings
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    llm_model: str = Field("gpt-4o-mini", env="LLM_MODEL")
    
    # Crawling settings
    max_crawl_depth: int = Field(2, env="MAX_CRAWL_DEPTH")
    max_concurrent_crawls: int = Field(5, env="MAX_CONCURRENT_CRAWLS")
    
    # Output settings
    default_markdown_output_dir: str = Field("./output", env="DEFAULT_MARKDOWN_OUTPUT_DIR")
    
    # Logging settings
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # GitHub settings
    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    github_repo: str = Field("unclecode/crawl4ai", env="GITHUB_REPO")
    
    # Documentation settings
    docs_url: str = Field("https://docs.crawl4ai.com", env="DOCS_URL")
    
    class Config:
        """Pydantic config"""
        env_file = ".env"
        case_sensitive = False


# Create global settings instances
settings = Settings()
github_config = GitHubConfig()
