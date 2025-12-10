"""
Utilitaire de logging centralisé
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from .config import LOG_LEVEL, LOG_FORMAT, PROJECT_ROOT


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Configure un logger avec formatage cohérent
    
    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Chemin optionnel vers un fichier de log
    
    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(level or LOG_LEVEL)
    
    # Éviter les doublons de handlers
    if logger.handlers:
        return logger
    
    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Handler fichier (optionnel)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# Logger par défaut
default_logger = setup_logger(
    'whatsapp_price_intelligence',
    log_file=PROJECT_ROOT / 'logs' / 'app.log'
)
