"""
Configuration settings for the crawl4ai-rag application.
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


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


# Create a global settings instance
settings = Settings()
