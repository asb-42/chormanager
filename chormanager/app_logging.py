"""Logging configuration for ChorManager."""

import logging
import logging.handlers  # noqa: F401
import sys
from pathlib import Path
from datetime import datetime

from .config import load_app_config, get_data_dir


def setup_logging():
    """Set up logging for ChorManager."""
    config = load_app_config()
    
    if not config.get("logging", {}).get("enabled", True):
        logging.basicConfig(level=logging.WARNING)
        return
    
    log_config = config["logging"]
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "chormanager.log"
    max_bytes = log_config.get("max_bytes", 10485760)  # 10 MB
    backup_count = log_config.get("backup_count", 5)
    level = getattr(logging, log_config.get("level", "INFO"))
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("ChorManager logging initialized")
    logging.info(f"Log file: {log_file}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.
    
    Args:
        name: Logger name (usually __name__).
        
    Returns:
        logging.Logger: Configured logger.
    """
    return logging.getLogger(name)
