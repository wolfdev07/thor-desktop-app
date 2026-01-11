"""Logging configuration using loguru."""
import sys
from loguru import logger
from config.settings import LOG_FILE, LOG_LEVEL, LOG_ROTATION, LOG_RETENTION


def setup_logger():
    """Configure application logger."""
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True,
    )
    
    # Add file handler
    logger.add(
        LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
    )
    
    return logger


# Initialize logger
app_logger = setup_logger()
