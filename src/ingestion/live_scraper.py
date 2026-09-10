import os
import sys
import json
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests
import urllib3

urllib3.disable_warnings()

from src.models.listing import RawListing, CleanedListing
from src.ingestion.collector import IngestionPipeline
from src.storage.database import PropertyDatabase
from src.utils.logger import get_logger
from src.utils.log_analyzer import PipelineAuditor
from src.domain.agencies_directory import resolve_agency_name

logger = get_logger("live_scraper")


class LiveNCScraper:
    """
    Scraper en direct multi-sources connecté :
    1. À l'API publique de Nouvelle-Calédonie (immobilier.nc / bienmeloger.nc)
       couvrant la fédération des 52 agences professionnelles de NC (3 300+ ventes et 3 000+ locations).
    2. À l'API GraphQL Cloud Function de Yatoo.nc (petites annonces ventes & locations).
    """

    API_POSTS_URL = "https://api.immobilier.nc/api/posts"
    YATOO_GRAPHQL_URL = "https://australia-southeast1-yatoo-nc.cloudfunctions.net/api"

    HEADERS_IMMO_NC = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, application/vnd_api.immobilier.nc.v0.1+json;",
        "Referer": "https://www.immobilier.nc/",
    }

    HEADERS_YATOO = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Origin": "https://yatoo.nc",
        "Referer": "https://yatoo.nc/",
    }

    def __init__(self, db: Optional[PropertyDatabase] = None):
        self.pipeline = IngestionPipeline(db=db)
        self.db = self.pipeline.db
        self.auditor = PipelineAuditor(db=self.db)

    def fetch_live_raw_items(self, deal_type: str = "vente", page: int = 1) -> List[Dict[str, Any]]:
        """Interroge l'API live immobilier.nc et renvoie la liste brute des données JSON."""
        params = {
            "by_deal_type": deal_type,
            "page": page,
        }
        logger.info(f"Connexion au flux en direct NC : {self.API_POSTS_URL} (page={page}, by_deal_type={deal_type})")
        try:
            resp = requests.get(self.API_POSTS_URL, params=params, headers=self.HEADERS_IMMO_NC, timeout=14, verify=False)
            resp.raise_for_status()
            payload = resp.json()
            items = payload.get("data", [])
            total = payload.get("meta", {}).get("total", len(items))
            logger.info(f"Flux NC page {page} ({deal_type}) : {len(items)} annonces reçues (Total disponible en NC : {total}).")
            return items
        except Exception as e:
            logger.error(f"Erreur de connexion à l'API en direct NC (page {page}, {deal_type}) : {e}")
            return []

    def parse_item_to_raw_listing(self, item: Dict[str, Any], default_source: str = "immobilier.nc") -> Optional[RawListing]:
        """Convertit un objet JSON issu de l'API NC en RawListing standardisé."""
        try:
            item_id = str(item.get("id"))
            if not item_id:
                return None

            # 1. Localisation
            locality = item.get("locality") or {}
            commune_name = (locality.get("name") or "").strip()
            quartier_dict = locality.get("children") or {}
            quartier_name = ""
            if isinstance(quartier_dict, dict):
                quartier_name = (quartier_dict.get("name") or "").strip()

            location_str = f"{commune_name} - {quartier_name}".strip(" -")

            # 2. Détection du type de transaction (Vente vs Location)
            deal_type_api = str(item.get("deal_type") or "").strip().lower()
            desc = item.get("description") or ""
            blob = f"{desc} {item.get('title') or ''}".lower()
            has_loc_words = bool(re.search(r"\b(location|louer|loyer|f/mois|charges comprises|bail)\b", blob))
            has_vente_words = bool(re.search(r"\b(vente|vendre|achat|acheter|prix fai)\b", blob))

            if deal_type_api == "location" or (has_loc_words and not has_vente_words):
                is_location = True
                transaction_type_declared = "Location"
            else:
                is_location = False
                transaction_type_declared = "Vente"

            # 3. Gestion et normalisation du Prix en F CFP
            raw_p = item.get("price")
            price_str = None
            if raw_p is not None:
                try:
                    p_val = float(raw_p)
                    if is_location:
                        # Pour une location : loyer mensuel
                        if p_val < 1000:
                            price_int = int(p_val * 1_000)
                        else:
                            price_int = int(p_val)
                        price_str = f"{price_int} F CFP/mois"
                    else:
                        # Pour une vente :
                        if p_val < 1000:
                            price_int = int(p_val * 1_000_000)
                        elif p_val >= 1_000_000:
                            price_int = int(p_val)
                        else:
                            if has_loc_words:
                                is_location = True
                                transaction_type_declared = "Location"
                                price_int = int(p_val)
                                price_str = f"{price_int} F CFP/mois"
                            else:
                                price_int = int(p_val * 1_000)
                                price_str = f"{price_int} F CFP"
                        if not price_str:
                            price_str = f"{price_int} F CFP"
                except (ValueError, TypeError):
                    price_str = str(raw_p)

            # 4. Surface habitable
            h_size = item.get("home_size")
            surface_str = f"{h_size} m²" if h_size is not None else None

            # 5. Détection du type de bien et titre
            prop_cat = str(item.get("property_category") or "").upper()
            prop_type = str(item.get("property_type") or "").capitalize()
            if not prop_type:
                prop_type = "Bien immobilier"

            title = f"{prop_type} {prop_cat} à {commune_name.capitalize()}".strip()
            if quartier_name:
                title += f" ({quartier_name.capitalize()})"

            # 6. Agence ou propriétaire avec résolution dans le référentiel des 52 agences NC
            owner = item.get("owner") or {}
            raw_owner_name = owner.get("full_name") or ""
            raw_mail = owner.get("mail") or ""
            
            # Liens externes partenaires (ex: soleil.nc)
            link_blob = ""
            for lk in (item.get("links") or []):
                if isinstance(lk, dict):
                    link_blob += " " + str(lk.get("path") or "")

            agency_name = resolve_agency_name(
                raw_name=raw_owner_name,
                raw_mail=raw_mail,
                text_blob=f"{desc} {link_blob}"
            )

            # 7. Détection de la source précise et photo authentique
            source = default_source
            photos = item.get("photos") or []
            photo_url = ""
            if photos and isinstance(photos, list):
                p0 = photos[0]
                if isinstance(p0, dict):
                    photo_url = p0.get("picture") or p0.get("thumbnail") or ""
                    if "bienmeloger.nc" in photo_url:
                        source = "bienmeloger.nc"

            url = f"https://www.immobilier.nc/details/{item_id}"
            if photo_url:
                desc = f"[IMG: {photo_url}] {desc}"

            return RawListing(
                source=source,
                source_id=item_id,
                url=url,
                title=title,
                description=desc,
                raw_price=price_str,
                raw_surface=surface_str,
                raw_rooms=prop_cat,
                raw_location=location_str,
                transaction_type_declared=transaction_type_declared,
                property_type_declared=prop_type,
                agency_name=agency_name,
                image_url=photo_url or None,
                extracted_at=datetime.now(timezone.utc),
            )
        except Exception as err:
            logger.warning(f"Impossible de convertir l'annonce brute {item.get('id')} : {err}")
            return None

    def fetch_yatoo_raw_items(self, category: str = "ventes-immobilieres", limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
        """Interroge l'API GraphQL native de Yatoo.nc pour extraire les petites annonces immobilières."""
        query = """
        query getSearchPosts($queryVariables: searchParams) {
          searchPosts(searchParams: $queryVariables) {
            data {
              id
              additionalType
              title
              media
              photos
              price
              sid
              category
              town
              description
              createdAt
              updatedAt
              userName
            }
            total
          }
        }
        """
        payload = {
            "operationName": "getSearchPosts",
            "variables": {
                "queryVariables": {
                    "category": category,
                    "limit": limit,
                    "page": page
                }
            },
            "query": query
        }
        try:
            logger.info(f"Interrogation API GraphQL Yatoo.nc ({category}, page={page}, limit={limit})...")
            resp = requests.post(self.YATOO_GRAPHQL_URL, json=payload, headers=self.HEADERS_YATOO, timeout=12, verify=False)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("searchPosts", {}).get("data", [])
            total = data.get("data", {}).get("searchPosts", {}).get("total", len(posts))
            logger.info(f"Yatoo.nc ({category}) : {len(posts)} annonces reçues (Total : {total}).")
            return posts
        except Exception as e:
            logger.error(f"Erreur lors de la requête GraphQL Yatoo.nc ({category}) : {e}")
            return []

    def parse_yatoo_item_to_raw_listing(self, item: Dict[str, Any], category: str = "ventes-immobilieres") -> Optional[RawListing]:
        """Convertit une petite annonce Yatoo.nc en RawListing standardisé."""
        try:
            item_id = str(item.get("id"))
            if not item_id:
                return None

            title = str(item.get("title") or "Annonce Immobilière Yatoo").strip()
            desc = str(item.get("description") or "").strip()
            town = str(item.get("town") or "Nouméa").strip()
            raw_price = item.get("price")
            is_loc = "locat" in category.lower() or "louer" in title.lower() or "loyer" in desc.lower()

            price_str = None
            if raw_price is not None:
                try:
                    p_val = float(raw_price)
                    price_int = int(p_val)
                    price_str = f"{price_int} F CFP/mois" if is_loc else f"{price_int} F CFP"
                except (ValueError, TypeError):
                    price_str = str(raw_price)

            # Photos Yatoo
            photos = item.get("photos") or []
            photo_url = ""
            if photos and isinstance(photos, list):
                p0 = photos[0]
                if isinstance(p0, dict):
                    photo_url = p0.get("contentUrl") or ""
                    if not photo_url:
                        thumbs = p0.get("thumbnail") or []
                        if thumbs and isinstance(thumbs, list) and isinstance(thumbs[0], dict):
                            photo_url = thumbs[0].get("contentUrl") or ""

            # Inférence du type de bien
            lower_text = f"{title} {desc}".lower()
            if "dock" in lower_text or "entrepot" in lower_text or "entrepôt" in lower_text:
                prop_type = "Dock"
            elif "terrain" in lower_text:
                prop_type = "Terrain"
            elif "appartement" in lower_text or "f1" in lower_text or "f2" in lower_text or "f3" in lower_text or "studio" in lower_text:
                prop_type = "Appartement"
            else:
                prop_type = "Maison"

            sid = item.get("sid") or item_id
            url = f"https://yatoo.nc/annonces/{category}/{sid}"
            if photo_url:
                desc = f"[IMG: {photo_url}] {desc}"

            agency_name = resolve_agency_name(
                raw_name=item.get("userName"),
                raw_mail=None,
                text_blob=f"{title} {desc}"
            )

            return RawListing(
                source="yatoo.nc",
                source_id=item_id,
                url=url,
                title=title,
                description=desc,
                raw_price=price_str,
                raw_surface=None,
                raw_rooms=None,
                raw_location=town,
                transaction_type_declared="Location" if is_loc else "Vente",
                property_type_declared=prop_type,
                agency_name=agency_name,
                image_url=photo_url or None,
                extracted_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"Erreur conversion Yatoo item {item.get('id')} : {e}")
            return None

    def run_live_sync(
        self,
        max_pages: int = 10,
        include_rentals: bool = True,
        include_yatoo: bool = True,
        source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exécute la synchronisation en direct multi-sources complète :
        1. Télécharge les ventes et locations depuis api.immobilier.nc (Fédération des 52 agences NC)
        2. Télécharge les petites annonces en direct depuis Yatoo.nc (GraphQL)
        3. Convertit et valide via RawListing
        4. Traite via IngestionPipeline (Cleaner + Enricher)
        5. Stocke/met à jour dans DuckDB
        6. Effectue l'audit de qualité et de santé du système
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"=== DEMARRAGE DU SCAN MULTI-SOURCES REEL (Pages: 1 à {max_pages}) ===")

        all_raw_listings: List[RawListing] = []

        # 1. SCAN DE LA PASSERELLE CENTRALE NC (IMMOBILIER.NC / BIENMELOGER.NC - 52 AGENCES)
        if not source_filter or "immobilier" in source_filter.lower() or "bienmeloger" in source_filter.lower():
            # A. VENTES
            for page in range(1, max_pages + 1):
                items = self.fetch_live_raw_items(deal_type="vente", page=page)
                for it in items:
                    rl = self.parse_item_to_raw_listing(it)
                    if rl:
                        all_raw_listings.append(rl)

            # B. LOCATIONS
            if include_rentals:
                rental_pages = max(2, min(max_pages, 10))
                for page in range(1, rental_pages + 1):
                    items = self.fetch_live_raw_items(deal_type="location", page=page)
                    for it in items:
                        rl = self.parse_item_to_raw_listing(it)
                        if rl:
                            all_raw_listings.append(rl)

        # 2. SCAN EN DIRECT DE YATOO.NC (GRAPHQL)
        if include_yatoo and (not source_filter or "yatoo" in source_filter.lower()):
            for y_cat in ["ventes-immobilieres", "locations"]:
                y_items = self.fetch_yatoo_raw_items(category=y_cat, limit=50, page=1)
                for it in y_items:
                    rl = self.parse_yatoo_item_to_raw_listing(it, category=y_cat)
                    if rl:
                        all_raw_listings.append(rl)

        if source_filter:
            all_raw_listings = [
                rl for rl in all_raw_listings
                if source_filter.lower() in rl.source.lower()
            ]

        logger.info(f"Total annonces brutes collectées prêtes pour ETL : {len(all_raw_listings)}")

        # 3. Exécution du pipeline d'ingestion vers DuckDB
        etl_result = self.pipeline.process_and_store(all_raw_listings, batch_tag="live_multi_sync")

        # 4. Exécution de l'audit de santé
        audit_summary = self.auditor.run_full_audit()
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

        # 5. Compte total actuel en base
        total_in_db = self.db.query("SELECT COUNT(*) AS c FROM listings WHERE is_active=TRUE").iloc[0]["c"]

        # Répartition par source
        source_breakdown = self.db.query("""
            SELECT source, COUNT(*) AS count
            FROM listings
            WHERE is_active=TRUE
            GROUP BY source
        """).to_dict(orient="records")

        logger.info(
            f"=== SCAN REEL TERMINE EN {duration_sec:.2f}s : "
            f"{etl_result['stored_cleaned']} traitées/insérées, "
            f"Total actif DuckDB : {total_in_db} annonces. Statut audit : {audit_summary.get('status')} ==="
        )

        return {
            "success": True,
            "duration_seconds": round(duration_sec, 2),
            "fetched_count": len(all_raw_listings),
            "stored_cleaned": etl_result["stored_cleaned"],
            "rejected_count": etl_result["rejected"],
            "total_in_db": int(total_in_db),
            "sources_summary": source_breakdown,
            "audit_status": audit_summary.get("status", "HEALTHY"),
            "audit_summary": audit_summary,
        }


if __name__ == "__main__":
    scraper = LiveNCScraper()
    res = scraper.run_live_sync(max_pages=2, include_rentals=True, include_yatoo=True)
    print(json.dumps(res, indent=2))
