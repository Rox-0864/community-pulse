"""
CommunityLab — Logger centralizado.

Responsable: Backend Developer
"""

import logging
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def setup_logger(name: str = "communitylab") -> logging.Logger:
    """Configura y retorna un logger para el módulo."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(LOG_LEVEL)
    return logger
