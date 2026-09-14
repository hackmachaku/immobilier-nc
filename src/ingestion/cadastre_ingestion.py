"""
Module d'ingestion et d'initialisation des référentiels Cadastre & REFIL (data.gouv.nc)
Fournit les fonctions pour télécharger, charger et indexer les parcelles et immeubles
de Nouvelle-Calédonie dans DuckDB.
"""

import os
import ssl
import logging
import urllib.request
from pathlib import Path
import duckdb

logger = logging.getLogger(__name__)

DATA_GOUV_PARCELLES_URL = (
    "https://data.gouv.nc/api/v2/catalog/datasets/parcelles-cadastrales-nc/exports/parquet"
)
DATA_GOUV_REFIL_URL = (
    "https://data.gouv.nc/api/v2/catalog/datasets/referentiel-des-immeubles-localises-refil/exports/parquet"
)

DEFAULT_CADASTRE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cadastre"


def ensure_cadastre_data(target_dir: Path | None = None) -> tuple[Path, Path]:
    """
    Vérifie la présence des fichiers Parquet locaux pour le Cadastre et REFIL.
    Les télécharge depuis data.gouv.nc si absents.
    Retourne les chemins (parcelles_path, refil_path).
    """
    dest_dir = target_dir or DEFAULT_CADASTRE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    parcelles_file = dest_dir / "parcelles_nc.parquet"
    refil_file = dest_dir / "refil_nc.parquet"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {"User-Agent": "Mozilla/5.0 (ImmobilierNC/1.0; OpenData Ingestion)"}

    if not parcelles_file.exists() or parcelles_file.stat().st_size < 1000:
        logger.info("Téléchargement du Cadastre NC (data.gouv.nc)...")
        req = urllib.request.Request(DATA_GOUV_PARCELLES_URL, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = resp.read()
            with open(parcelles_file, "wb") as f:
                f.write(data)
        logger.info("Cadastre NC téléchargé avec succès : %s octets", len(data))

    if not refil_file.exists() or refil_file.stat().st_size < 1000:
        logger.info("Téléchargement du référentiel REFIL NC (data.gouv.nc)...")
        req = urllib.request.Request(DATA_GOUV_REFIL_URL, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = resp.read()
            with open(refil_file, "wb") as f:
                f.write(data)
        logger.info("REFIL NC téléchargé avec succès : %s octets", len(data))

    return parcelles_file, refil_file


def init_cadastre_tables(con: duckdb.DuckDBPyConnection, cadastre_dir: Path | None = None) -> None:
    """
    Initialise l'extension spatiale DuckDB et configure les vues sur le Cadastre et REFIL.
    """
    parcelles_file, refil_file = ensure_cadastre_data(cadastre_dir)
    parcelles_str = str(parcelles_file).replace("\\", "/")
    refil_str = str(refil_file).replace("\\", "/")

    # Activer l'extension spatiale
    try:
        con.execute("INSTALL spatial;")
    except Exception:
        pass
    try:
        con.execute("LOAD spatial;")
    except Exception as e:
        logger.warning("Impossible de charger l'extension spatial DuckDB: %s", e)

    # Créer les vues permanentes ou tables
    con.execute(f"""
        CREATE VIEW IF NOT EXISTS cadastre_parcelles AS
        SELECT * FROM '{parcelles_str}'
    """)

    con.execute(f"""
        CREATE VIEW IF NOT EXISTS cadastre_refil AS
        SELECT * FROM '{refil_str}'
    """)
    logger.info("Vues cadastre_parcelles et cadastre_refil créées dans DuckDB.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p_path, r_path = ensure_cadastre_data()
    print(f"Parcelles: {p_path} (taille: {p_path.stat().st_size} octets)")
    print(f"REFIL: {r_path} (taille: {r_path.stat().st_size} octets)")
    test_con = duckdb.connect()
    init_cadastre_tables(test_con)
    p_count = test_con.execute("SELECT count(*) FROM cadastre_parcelles").fetchone()[0]
    r_count = test_con.execute("SELECT count(*) FROM cadastre_refil").fetchone()[0]
    print(f"Comptage: {p_count} parcelles, {r_count} immeubles REFIL.")
