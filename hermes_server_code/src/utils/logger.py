import sys
from pathlib import Path
from loguru import logger

LOGS_DIR = Path("logs")


def setup_logger(log_level: str = "INFO"):
    """Setup loguru logger with file rotation and console output"""

    # Create logs directory if it doesn't exist
    LOGS_DIR.mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # Add console handler with color
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # Add file handler with rotation
    logger.add(
        LOGS_DIR / "crypto_monitor_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return logger


# Global logger instance
logger = setup_logger()
