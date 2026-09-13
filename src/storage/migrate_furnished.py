"""
Script de migration et de rétro-remplissage (backfill) de la colonne is_furnished.
Analyse l'ensemble des annonces existantes en base DuckDB et applique la logique de détection de l'ameublement.
"""
from src.storage.database import PropertyDatabase
from src.processing.cleaner import ListingCleaner
from src.models.listing import PropertyType, TransactionType

def run_migration():
    print("Démarrage de la migration de l'ameublement (is_furnished)...")
    db = PropertyDatabase()
    cleaner = ListingCleaner()

    with db.get_connection() as con:
        # 1. S'assurer que la colonne existe
        con.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_furnished BOOLEAN;")

        # 2. Récupérer toutes les annonces
        df = con.execute("""
            SELECT id, title, description, property_type, transaction_type 
            FROM listings
        """).df()

        print(f"Total annonces à analyser : {len(df)}")

        count_meuble = 0
        count_non_meuble = 0
        count_none = 0

        updates = []
        for _, row in df.iterrows():
            item_id = str(row["id"])
            title = str(row["title"] or "")
            desc = str(row["description"] or "")
            pt_str = str(row["property_type"] or "").upper()
            tt_str = str(row["transaction_type"] or "").upper()

            try:
                prop_type = PropertyType(pt_str)
            except Exception:
                prop_type = PropertyType.AUTRE

            try:
                trans_type = TransactionType(tt_str)
            except Exception:
                trans_type = TransactionType.VENTE

            # Extraction de l'ameublement
            is_furnished = cleaner.parse_furnished(
                facilities=None,
                title=title,
                description=desc,
                property_type=prop_type,
                transaction_type=trans_type,
            )

            if is_furnished is True:
                count_meuble += 1
            elif is_furnished is False:
                count_non_meuble += 1
            else:
                count_none += 1

            updates.append((is_furnished, item_id))

        # 3. Mise à jour par lot en base
        con.executemany("UPDATE listings SET is_furnished = ? WHERE id = ?", updates)

        print("\n--- Résultat de la migration ---")
        print(f"Meublé (True)      : {count_meuble}")
        print(f"Non meublé (False) : {count_non_meuble}")
        print(f"Non spécifié (None): {count_none}")
        print("Migration DuckDB terminée avec succès !")

if __name__ == "__main__":
    run_migration()
