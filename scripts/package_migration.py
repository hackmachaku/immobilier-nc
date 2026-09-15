#!/usr/bin/env python3
"""
Script autonome d'empaquetage pour la migration complète du projet Immobilier NC.
Génère une archive ZIP complète 'migration_bundle_immobilier_nc.zip' prête à être
transférée sur un nouvel ordinateur (clé USB, disque dur externe, cloud drive).
"""

import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime

# Assurer l'encodage UTF-8 sur console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent

# Liste des répertoires et fichiers à exclure formellement
EXCLUDE_DIRS = {
    ".venv", "venv", "ENV", ".git", "__pycache__", 
    ".pytest_cache", ".pytest_temp", ".idea", ".vscode"
}

EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".tmp"
}

EXCLUDE_FILES = {
    "cloudflared.exe", "migration_bundle_immobilier_nc.zip"
}


def should_include_file(file_path: Path) -> bool:
    """Détermine si un fichier doit être inclus dans le bundle de migration."""
    # Vérifier si l'un des parents est dans la liste des dossiers exclus
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False
            
    # Vérifier le nom de fichier
    if file_path.name in EXCLUDE_FILES or file_path.name.startswith("migration_bundle_"):
        return False
        
    # Vérifier l'extension
    if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return False
        
    return True


def create_migration_bundle(output_zip: Path) -> None:
    """Crée l'archive ZIP de migration complète."""
    print("=" * 70)
    print("📦 PRÉPARATION DE L'ARCHIVE DE MIGRATION IMMOBILIER NC")
    print(f"📂 Répertoire racine : {BASE_DIR}")
    print(f"🎯 Fichier cible     : {output_zip}")
    print("=" * 70)

    total_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Élaguer les dossiers exclus pour accélérer le parcours
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                file_path = Path(root) / file
                if should_include_file(file_path):
                    rel_path = file_path.relative_to(BASE_DIR)
                    zipf.write(file_path, arcname=rel_path)
                    total_files += 1
                    total_uncompressed_bytes += file_path.stat().st_size

    compressed_size_mb = output_zip.stat().st_size / (1024 * 1024)
    uncompressed_size_mb = total_uncompressed_bytes / (1024 * 1024)

    print("\n✅ ARCHIVE DE MIGRATION GÉNÉRÉE AVEC SUCCÈS !")
    print(f"📄 Nombre total de fichiers inclus : {total_files}")
    print(f"💾 Taille non compressée          : {uncompressed_size_mb:.2f} Mo")
    print(f"🗜️  Taille de l'archive ZIP         : {compressed_size_mb:.2f} Mo")
    print(f"📍 Emplacement exact               : {output_zip.resolve()}")
    print("=" * 70)
    print("📋 PROCHAINES ÉTAPES POUR LE NOUVEL ORDINATEUR :")
    print("1. Copiez cette archive ZIP sur votre clé USB ou disque externe.")
    print("2. Décompressez-la sur le nouvel ordinateur.")
    print("3. Suivez les instructions indiquées dans le fichier 'MIGRATION.md'.")
    print("=" * 70)


if __name__ == "__main__":
    target_zip = BASE_DIR / "migration_bundle_immobilier_nc.zip"
    create_migration_bundle(target_zip)
