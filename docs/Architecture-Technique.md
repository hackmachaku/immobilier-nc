# 🛠️ Architecture Technique & Pipeline de Données

Ce document décrit l'architecture logicielle, les technologies employées et le flux de traitement ETL.

---

## 1. Stack Technologique

- **Langage** : Python 3.12+ (standard typé, Pydantic v2).
- **Base de Données** : [DuckDB](https://duckdb.org/) (moteur analytique OLAP ultra-rapide embarqué en local).
- **Frontend** :
  - HTML5 / Vanilla JavaScript (zéro dépendance lourde, réactivité instantanée).
  - [Tailwind CSS](https://tailwindcss.com/) pour l'interface sombre (Dark Mode).
  - [Leaflet.js](https://leafletjs.com/) pour la cartographie interactive du Grand Nouméa.
- **Hébergement Web** : GitHub Pages (CDN mondial SSL 100% gratuit).

---

## 2. Pipeline ETL (Extract - Transform - Load)

```
[ Sources Web NC ]
   ├── api.immobilier.nc (REST)
   ├── bienmeloger.nc (REST)
   └── yatoo.nc (GraphQL)
            │
            ▼
[ 1. Ingestion / Scraper ] (live_scraper.py)
   └── Création d'archives brutes (.jsonl)
            │
            ▼
[ 2. Nettoyage & Normalisation ] (cleaner.py)
   ├── Détection Vente vs Location
   ├── Normalisation des loyers (mensuels) vs prix de vente (Millions)
   ├── Conversion des surfaces calédoniennes (ares ➔ m²)
   └── Résolution de l'agence propriétaire (agencies_directory.py)
            │
            ▼
[ 3. Enrichissement Métier ] (enricher.py)
   ├── Calcul prix/m² et loyer/m²
   ├── Benchmark sectoriel (quartier)
   └── Diagnostic IA & marge de négociation
            │
            ▼
[ 4. Stockage Analytique DuckDB ] (database.py)
   ├── Table principale : listings (avec index unique)
   └── Vues SQL : v_marche_par_quartier, v_marche_par_typologie
            │
            ▼
[ 5. Export Statique Cloud ] (export_static_data.py)
   └── Génération de data_listings.json et data_agencies.json pour GitHub Pages
```

---

## 3. Spécificités Calédoniennes Gérées

- **Monnaie locale** : Franc Pacifique (XPF / F CFP) avec parité fixe Euros (1 EUR = 119.3317 XPF).
- **Unités de surface** : Prise en compte des **ares** (1 are = 100 m²), très fréquents dans les annonces de terrains et de villas en brousse ou sur Savannah / Païta / Dumbéa.
- **Éléments architecturaux locaux** :
  - Varangues couvertes et decks valorisés à 35% de la surface habitable.
  - Docks industriels (Ducos, Numbo).
  - Propriétés de bord de mer et rivière.
