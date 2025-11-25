"""
Logging configuration
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "whatsapp_api") -> logging.Logger:
    """Setup logger with console and file handlers"""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "api.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(console_format)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


# Default logger
logger = setup_logger()
