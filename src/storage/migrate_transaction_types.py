import glob
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from src.storage.database import PropertyDatabase
from src.processing.cleaner import ListingCleaner
from src.models.listing import TransactionType
from src.utils.logger import get_logger

logger = get_logger("migrate_transaction_types")


def load_raw_declarations() -> Dict[str, Dict[str, Any]]:
    """Indexe les déclarations d'origine (deal_type, raw_price) depuis tous les fichiers raw JSONL."""
    raw_map: Dict[str, Dict[str, Any]] = {}
    for f in sorted(glob.glob("data/raw/*.jsonl")):
        with open(f, "r", encoding="utf-8", errors="ignore") as infile:
            for line in infile:
                try:
                    d = json.loads(line)
                    src_id = str(d.get("source_id") or "")
                    source = str(d.get("source") or "")
                    if src_id and source:
                        key = f"{source}_{src_id}"
                        # Les fichiers plus récents écrasent les plus anciens
                        raw_map[key] = {
                            "declared": d.get("transaction_type_declared"),
                            "raw_price": d.get("raw_price"),
                            "title": d.get("title"),
                            "property_type_declared": d.get("property_type_declared"),
                        }
                except Exception:
                    continue
    return raw_map


def run_migration():
    print("=== Démarrage de l'assainissement et de la re-classification des transactions ===")
    db = PropertyDatabase()
    cleaner = ListingCleaner()

    raw_meta = load_raw_declarations()
    print(f"Métadonnées brutes chargées pour {len(raw_meta)} annonces sources.")

    with db.get_connection() as con:
        rows = con.execute("""
            SELECT id, source, source_id, title, description, transaction_type, property_type, price_xpf, surface_habitable_m2
            FROM listings
        """).fetchall()

        print(f"Total annonces analysées en base : {len(rows)}")

        updates = []
        changes_to_loc = []
        changes_to_vente = []

        for r in rows:
            lid, src, src_id, title, desc, curr_tt, prop_type, price, surface = r
            
            meta = raw_meta.get(lid, {})
            declared = meta.get("declared")
            raw_price = meta.get("raw_price")

            # Détection avec les nouvelles règles financières et sémantiques robustes
            new_tt = cleaner.detect_transaction_type(
                declared=declared,
                title=title or "",
                description=desc or "",
                price=price,
                raw_price_str=raw_price,
            )

            if new_tt.value != curr_tt:
                updates.append((new_tt.value, lid))
                detail = f"[{lid}] {title} | Prix: {price:,} F | Ancien: {curr_tt} -> Nouveau: {new_tt.value}".replace(",", " ")
                if new_tt == TransactionType.LOCATION:
                    changes_to_loc.append(detail)
                else:
                    changes_to_vente.append(detail)

        print(f"\nTotal corrections à appliquer : {len(updates)}")
        print(f"  - Reclassés en LOCATION ({len(changes_to_loc)}) :")
        for c in changes_to_loc:
            print(f"    • {c}")

        print(f"  - Reclassés en VENTE ({len(changes_to_vente)}) :")
        for c in changes_to_vente:
            print(f"    • {c}")

        if updates:
            con.executemany("UPDATE listings SET transaction_type = ? WHERE id = ?", updates)
            print(f"\n[OK] Mise à jour de {len(updates)} annonces validée dans DuckDB !")
        else:
            print("\nAucune incohérence détectée.")

        # Contrôle post-migration
        anomalies_ventes = con.execute("""
            SELECT count(*) FROM listings WHERE transaction_type = 'VENTE' AND price_xpf < 1500000
        """).fetchone()[0]

        anomalies_locs = con.execute("""
            SELECT count(*) FROM listings WHERE transaction_type = 'LOCATION' AND price_xpf > 3000000
        """).fetchone()[0]

        print("\n--- CONTRÔLE QUALITÉ POST-MIGRATION ---")
        print(f"Ventes suspectes (< 1 500 000 F CFP) : {anomalies_ventes}")
        print(f"Locations suspectes (> 3 000 000 F CFP) : {anomalies_locs}")
        assert anomalies_ventes == 0, f"Erreur : il reste {anomalies_ventes} ventes sous 1.5M !"
        assert anomalies_locs == 0, f"Erreur : il reste {anomalies_locs} locations au-dessus de 3M !"
        print("[SUCCESS] 100% de la base est saine et cohérente !")


if __name__ == "__main__":
    run_migration()
