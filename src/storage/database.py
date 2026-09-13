from pathlib import Path
from typing import List, Optional
import duckdb
import pandas as pd

from src.config.settings import DB_PATH, PROCESSED_DATA_DIR
from src.models.listing import RawListing, CleanedListing


class PropertyDatabase:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        # Assurer que le dossier parent existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def _init_schema(self):
        """Initialise les tables et vues analytiques DuckDB."""
        with self.get_connection() as con:
            # Table des annonces nettoyées
            con.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id VARCHAR PRIMARY KEY,
                source VARCHAR,
                source_id VARCHAR,
                url VARCHAR,
                title VARCHAR,
                description VARCHAR,
                transaction_type VARCHAR,
                property_type VARCHAR,
                commune VARCHAR,
                quartier VARCHAR,
                price_xpf BIGINT,
                price_eur DOUBLE,
                charges_mensuelles_xpf INTEGER,
                surface_habitable_m2 DOUBLE,
                surface_terrain_m2 DOUBLE,
                surface_terrasse_m2 DOUBLE,
                prix_m2_habitable_xpf DOUBLE,
                prix_m2_habitable_eur DOUBLE,
                rooms INTEGER,
                bedrooms INTEGER,
                bathrooms INTEGER,
                parkings INTEGER,
                has_sea_view BOOLEAN,
                has_pool BOOLEAN,
                has_air_conditioning BOOLEAN,
                is_secured BOOLEAN,
                is_furnished BOOLEAN,
                standing_estime VARCHAR,
                agency_name VARCHAR,
                image_url VARCHAR,
                images_json VARCHAR,
                published_at TIMESTAMP,
                scraped_at TIMESTAMP,
                is_active BOOLEAN
            );
            ALTER TABLE listings ADD COLUMN IF NOT EXISTS images_json VARCHAR;
            ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_furnished BOOLEAN;
            """)

            # Vues analytiques
            con.execute("""
            CREATE OR REPLACE VIEW v_marche_par_quartier AS
            SELECT 
                commune,
                quartier,
                transaction_type,
                property_type,
                COUNT(*) AS total_annonces,
                ROUND(MEDIAN(price_xpf), 0) AS prix_median_xpf,
                ROUND(AVG(price_xpf), 0) AS prix_moyen_xpf,
                ROUND(MEDIAN(prix_m2_habitable_xpf), 0) AS prix_m2_median_xpf,
                ROUND(AVG(prix_m2_habitable_xpf), 0) AS prix_m2_moyen_xpf,
                ROUND(AVG(prix_m2_habitable_eur), 1) AS prix_m2_moyen_eur,
                ROUND(AVG(surface_habitable_m2), 1) AS surface_hab_moyenne,
                SUM(CASE WHEN has_sea_view THEN 1 ELSE 0 END) AS nb_vue_mer,
                SUM(CASE WHEN has_pool THEN 1 ELSE 0 END) AS nb_piscine
            FROM listings
            WHERE is_active = TRUE AND prix_m2_habitable_xpf IS NOT NULL
            GROUP BY commune, quartier, transaction_type, property_type;
            """)

            # Vue de valorisation par typologie de pièces (F2, F3, F4, etc.)
            con.execute("""
            CREATE OR REPLACE VIEW v_marche_par_typologie AS
            SELECT 
                commune,
                property_type,
                rooms,
                transaction_type,
                COUNT(*) AS total_annonces,
                ROUND(MEDIAN(price_xpf), 0) AS prix_median_xpf,
                ROUND(MEDIAN(prix_m2_habitable_xpf), 0) AS prix_m2_median_xpf,
                ROUND(AVG(surface_habitable_m2), 1) AS surface_moyenne
            FROM listings
            WHERE is_active = TRUE AND rooms IS NOT NULL
            GROUP BY commune, property_type, rooms, transaction_type;
            """)

    def upsert_listings(self, listings: List[CleanedListing]):
        """Insère ou met à jour une liste d'annonces nettoyées."""
        if not listings:
            return

        records = []
        for l in listings:
            records.append({
                "id": l.id,
                "source": l.source,
                "source_id": l.source_id,
                "url": l.url,
                "title": l.title,
                "description": l.description,
                "transaction_type": l.transaction_type.value,
                "property_type": l.property_type.value,
                "commune": l.commune.value,
                "quartier": l.quartier,
                "price_xpf": l.price_xpf,
                "price_eur": l.price_eur,
                "charges_mensuelles_xpf": l.charges_mensuelles_xpf,
                "surface_habitable_m2": l.surface_habitable_m2,
                "surface_terrain_m2": l.surface_terrain_m2,
                "surface_terrasse_m2": l.surface_terrasse_m2,
                "prix_m2_habitable_xpf": l.prix_m2_habitable_xpf,
                "prix_m2_habitable_eur": l.prix_m2_habitable_eur,
                "rooms": l.rooms,
                "bedrooms": l.bedrooms,
                "bathrooms": l.bathrooms,
                "parkings": l.parkings,
                "has_sea_view": l.has_sea_view,
                "has_pool": l.has_pool,
                "has_air_conditioning": l.has_air_conditioning,
                "is_secured": l.is_secured,
                "is_furnished": l.is_furnished,
                "standing_estime": l.standing_estime,
                "agency_name": l.agency_name,
                "image_url": getattr(l, "image_url", None),
                "images_json": getattr(l, "images_json", None),
                "published_at": l.published_at,
                "scraped_at": l.scraped_at,
                "is_active": l.is_active,
            })

        df = pd.DataFrame(records)

        with self.get_connection() as con:
            # Insertion avec dédoublonnage (ON CONFLICT DO UPDATE)
            con.register("staging_df", df)
            con.execute("""
            INSERT INTO listings BY NAME
            SELECT * FROM staging_df
            ON CONFLICT (id) DO UPDATE SET
                description = EXCLUDED.description,
                price_xpf = EXCLUDED.price_xpf,
                price_eur = EXCLUDED.price_eur,
                charges_mensuelles_xpf = EXCLUDED.charges_mensuelles_xpf,
                surface_habitable_m2 = EXCLUDED.surface_habitable_m2,
                surface_terrain_m2 = EXCLUDED.surface_terrain_m2,
                surface_terrasse_m2 = EXCLUDED.surface_terrasse_m2,
                prix_m2_habitable_xpf = EXCLUDED.prix_m2_habitable_xpf,
                prix_m2_habitable_eur = EXCLUDED.prix_m2_habitable_eur,
                has_sea_view = EXCLUDED.has_sea_view,
                has_pool = EXCLUDED.has_pool,
                has_air_conditioning = EXCLUDED.has_air_conditioning,
                is_secured = EXCLUDED.is_secured,
                is_furnished = EXCLUDED.is_furnished,
                image_url = COALESCE(EXCLUDED.image_url, listings.image_url),
                images_json = COALESCE(EXCLUDED.images_json, listings.images_json),
                scraped_at = EXCLUDED.scraped_at,
                is_active = EXCLUDED.is_active;
            """)

    def query(self, sql: str) -> pd.DataFrame:
        """Exécute une requête SQL personnalisée et renvoie un DataFrame."""
        with self.get_connection() as con:
            return con.execute(sql).df()

    def get_market_summary(self) -> pd.DataFrame:
        """Retourne la synthèse des prix par quartier et type d'opération."""
        with self.get_connection() as con:
            return con.execute("""
            SELECT * FROM v_marche_par_quartier 
            ORDER BY commune, transaction_type, total_annonces DESC
            """).df()
