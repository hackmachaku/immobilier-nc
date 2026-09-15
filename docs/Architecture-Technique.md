# 🛠️ Architecture Technique & Pipeline de Données • Veille Immo NC Sentinel

Ce document décrit l'architecture logicielle, les technologies employées, le schéma de données DuckDB, le moteur spatial et le flux de traitement ETL.

---

## 1. Stack Technologique

- **Langage** : Python 3.12+ (standard typé, Pydantic v2).
- **Base de Données Analytique** : [DuckDB](https://duckdb.org/) (moteur SQL OLAP ultra-rapide embarqué en local avec support multi-threads et verrous concurrentiels `read_only`).
- **Moteur Spatial & Foncier** :
  - Formats Apache Parquet (`parcelles_nc.parquet` & `refil_nc.parquet`).
  - Index spatial 2D par grille projetée pour croisement géographique en mémoire.
  - Connexion directe à l'API ArcGIS REST de `cadastre.gouv.nc` (CORS natif).
- **Frontend** :
  - Single Page Application (SPA) HTML5 / Vanilla JavaScript (0 bundle JS lourd, temps de chargement éclair).
  - [Tailwind CSS](https://tailwindcss.com/) pour le thème sombre moderne (Dark Mode).
  - [Leaflet.js](https://leafletjs.com/) avec moteur de rendu direct **HTML5 Canvas GPU** (`preferCanvas: true`).
  - Fond de carte **CartoDB Voyager** propulsé par **Fastly Anycast Global CDN** avec mise en cache mémoire (`keepBuffer: 8`).
- **Hébergement & Déploiement** :
  - GitHub Pages (CDN mondial SSL gratuit).
  - Architecture Dual-Repo (`immobilier-nc` en production, `immobilier-nc-preview` en prévisualisation).

---

## 2. Pipeline ETL (Extract - Transform - Load)

```
[ 4 Sources Calédoniennes Réelles (2 683 annonces) ]
   ├── api.immobilier.nc (REST API - 702 annonces)
   ├── bienmeloger.nc (Passerelle agences - 477 annonces)
   ├── yatoo.nc (API GraphQL native - 95 annonces)
   └── immonc.com / immocal (Scraper XML/HTML - 1 409 annonces)
            │
            ▼
[ 1. Ingestion / Scraper ] (live_scraper.py)
   └── Création d'archives brutes horodatées (.jsonl dans data/raw/)
            │
            ▼
[ 2. Nettoyage & Normalisation ] (cleaner.py)
   ├── Distinction stricte Vente vs Location
   ├── Normalisation des loyers mensuels vs prix de vente en Millions
   ├── Conversion des ares en m² (1 are = 100 m²)
   └── Résolution des 52 agences partenaires (agencies_directory.py)
            │
            ▼
[ 3. Moteur Spatial & Cadastre DITTT ] (cadastre_enrichment.py)
   ├── Rattachement aux 77 051 parcelles officielles (NIC, Lot, Contenance notariée)
   ├── Résolution textuelle REFIL (3 890 résidences avec année de livraison)
   ├── Élimination des points maritimes / mangroves (Tina, Baie des Citrons, Ducos)
   └── Calcul des écarts de surface déclarée vs légale notariée
            │
            ▼
[ 4. Stockage Analytique DuckDB ] (database.py)
   ├── Table `listings` (dédoublonnage par ID source unique)
   ├── Préservation des baisses de prix : `initial_price_xpf = COALESCE(initial_price, EXCLUDED.price_xpf)`
   ├── Table `listing_price_history` (127 baisses de prix réelles historisées)
   └── Vues SQL analytiques : `v_marche_par_quartier`, `v_marche_par_typologie`
            │
            ▼
[ 5. Export Statique Cloud ] (export_static_data.py)
   └── Génération de data_listings.json, data_sources.json et data_agencies.json
```

---

## 3. Schéma de la Base DuckDB (`immobilier_grand_noumea.duckdb`)

### Table `listings`
| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | VARCHAR PRIMARY KEY | Identifiant unique normalisé (ex: `immonc_5328793`, `immo_450212`) |
| `source` | VARCHAR | Nom de la source (`immobilier.nc`, `bienmeloger.nc`, `yatoo.nc`, `immonc`) |
| `title` | VARCHAR | Titre de l'annonce immobilière |
| `transaction_type` | VARCHAR | `VENTE` ou `LOCATION` |
| `property_type` | VARCHAR | `MAISON`, `APPARTEMENT`, `TERRAIN`, `DOCK`, `COMMERCE`, etc. |
| `commune` | VARCHAR | Nom de la commune normalisée (`NOUMEA`, `DUMBEA`, `MONT-DORE`, `PAITA`...) |
| `quartier` | VARCHAR | Quartier calédonien précis |
| `price_xpf` | BIGINT | Prix actuel en Francs Pacifique |
| `initial_price_xpf` | BIGINT | Prix d'origine enregistré lors de la première détection |
| `price_eur` | DOUBLE | Équivalent Euro au taux fixe de 119.3317 |
| `surface_habitable_m2` | DOUBLE | Surface habitable en m² |
| `surface_terrain_m2` | DOUBLE | Surface du terrain en m² |
| `rooms` / `bedrooms` | INTEGER | Nombre de pièces et chambres (F2, F3, F4...) |
| `agency_name` | VARCHAR | Nom de l'agence ou `Particulier NC` |
| `image_url` | VARCHAR | Photo principale haute définition |
| `images_json` | VARCHAR | Tableau JSON de l'ensemble des photos |
| `cadastre_nic` | VARCHAR | Numéro d'Identification Cadastrale DITTT |
| `cadastre_lot` | VARCHAR | Numéro de lot géomètre |
| `cadastre_contenance` | VARCHAR | Contenance notariée officielle (ex: `0ha 9a 76ca`) |
| `refil_residence` | VARCHAR | Nom de l'immeuble ou de la résidence répertoriée |
| `refil_annee` | VARCHAR | Année de construction officielle |
| `first_seen_at` | TIMESTAMP | Date de première détection sous veille |
| `last_price_change_at` | TIMESTAMP | Date de la dernière variation de prix constatée |
| `is_active` | BOOLEAN | Statut actif de l'offre sur le marché |

### Table `listing_price_history`
| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | VARCHAR PRIMARY KEY | Identifiant unique de l'événement |
| `listing_id` | VARCHAR | Référence vers `listings.id` |
| `price_xpf` | BIGINT | Nouveau prix constaté |
| `price_change_xpf` | BIGINT | Écart en Francs Pacifique (ex: `-3 000 000`) |
| `price_change_pct` | DOUBLE | Pourcentage de baisse (ex: `-8.5%`) |
| `recorded_at` | TIMESTAMP | Horodatage précis du scan ayant détecté la baisse |
