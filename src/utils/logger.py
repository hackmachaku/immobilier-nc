import logging
import sys
from pathlib import Path
from typing import Optional

# Chemin vers le dossier logs
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_FILE = LOGS_DIR / "pipeline.log"

_is_configured = False


def setup_logger(
    name: str = "immo_nc",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure et retourne le logger centralisé du projet avec sortie console et fichier."""
    global _is_configured
    target_file = log_file or DEFAULT_LOG_FILE

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Éviter les handlers dupliqués
    if not logger.handlers:
        # Formateur détaillé
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )

        # 1. Handler Fichier (UTF-8 permanent pour audit)
        file_handler = logging.FileHandler(target_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 2. Handler Console (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    _is_configured = True
    return logger


def get_logger(name: str = "immo_nc") -> logging.Logger:
    """Récupère le logger configuré."""
    return logging.getLogger(name) if _is_configured else setup_logger(name)
