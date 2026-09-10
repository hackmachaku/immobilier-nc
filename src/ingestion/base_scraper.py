import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import requests

from src.config.settings import DEFAULT_HEADERS, DEFAULT_REQUEST_TIMEOUT, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from src.models.listing import RawListing

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Classe de base abstraite pour les scrapers de portails immobiliers calédoniens.
    Intègre les bonnes pratiques :
    - En-têtes HTTP réalistes
    - Délais aléatoires respectueux entre les requêtes
    - Gestion robuste des erreurs et des timeouts
    """

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _sleep_polite(self):
        """Pause aléatoire pour ne pas surcharger les serveurs sources."""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def fetch_url(self, url: str) -> Optional[str]:
        """Télécharge le contenu HTML d'une page avec gestion d'erreurs."""
        self._sleep_polite()
        try:
            response = self.session.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Erreur de téléchargement sur {url} : {e}")
            return None

    @abstractmethod
    def scrape_listings(self, max_pages: int = 3) -> List[RawListing]:
        """Méthode à implémenter par chaque scraper spécifique."""
        pass
