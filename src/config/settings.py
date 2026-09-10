from pathlib import Path
from typing import Dict, Any

# Root project directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REFERENCE_DATA_DIR = DATA_DIR / "reference"

# Database path (DuckDB)
DB_PATH = PROCESSED_DATA_DIR / "immobilier_grand_noumea.duckdb"

# Financial constants
# Parité officielle fixe Franc Pacifique (XPF) / Euro : 1 EUR = 119.33174 XPF
XPF_TO_EUR_RATE = 119.3317422

# Notary / Acquisition fees in New Caledonia (droits d'enregistrement et frais notariés en moyenne ~7.5% à 9%)
DEFAULT_NOTARY_FEES_RATIO = 0.08

# TGC (Taxe Générale sur la Consommation) : taux sur prestations immobilières et travaux (6% ou 11%)
TGC_IMMOBILIER_TAUX = 0.11

# Scraper settings
DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

DEFAULT_REQUEST_TIMEOUT = 15
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.5
