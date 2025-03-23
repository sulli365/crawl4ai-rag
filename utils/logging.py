"""
Logging configuration for the crawl4ai-rag application.
"""

import sys
import logging
from pathlib import Path
from loguru import logger
from typing import Dict, Any

from config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect them to loguru.
    """
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """
    Configure logging for the application.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure loguru
    config = {
        "handlers": [
            {
                "sink": sys.stderr,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                "level": settings.log_level,
            },
            {
                "sink": logs_dir / "crawl4ai-rag.log",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                "level": settings.log_level,
                "rotation": "10 MB",
                "retention": "1 month",
                "compression": "zip",
            },
        ],
    }

    # Remove default logger
    logger.remove()
    
    # Apply configuration
    for handler in config["handlers"]:
        logger.add(**handler)

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Replace standard library logging with loguru
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = [InterceptHandler()]

    # Set log levels for some noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)

    logger.info("Logging configured successfully")


def get_logger(name: str) -> logger:
    """
    Get a logger instance for the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        A logger instance
    """
    return logger.bind(name=name)
