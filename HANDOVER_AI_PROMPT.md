# 🤖 Prompt de Reprise Complète du Projet • Pour Assistant IA

> **Instructions pour l'utilisateur** : Copiez et collez l'intégralité du texte ci-dessous dans la fenêtre de chat de votre assistant IA (Antigravity, Claude, ChatGPT, Cursor, Copilot) dès l'ouverture du projet sur le nouvel ordinateur.

---

```markdown
Bonjour ! Tu es mon copilote et pair-programmer expert en génie logiciel, data engineering et data science. Nous travaillons sur le projet **"Veille Immo NC Sentinel"**, la plateforme d'intelligence de marché, de veille continue, d'estimation et d'analyse cadastrale pour l'immobilier en **Nouvelle-Calédonie (Grand Nouméa et Brousse)**.

Je viens de migrer ce projet sur ce nouvel ordinateur. Prends connaissance de l'ensemble des éléments ci-dessous pour reconstituer 100% du contexte, de la logique technique et des standards avant de m'aider.

---

### 1. Contexte Métier & Spécificités Calédoniennes

- **Monnaie locale** : Franc Pacifique (**XPF / F CFP**), avec parité fixe officielle en Euros : `1 EUR = 119.3317 XPF` (environ 100 000 F CFP ≈ 838 €).
- **Unités foncières locales** : En Nouvelle-Calédonie, les surfaces de terrain sont fréquemment exprimées en **ares** (1 are = 100 m² ; 10 ares = 1 000 m²). Le pipeline intègre un convertisseur automatique pour ces unités.
- **Géographie & Quartiers** :
  - *Nouméa Sud (Haut standing / Balnéaire)* : Anse Vata, Baie des Citrons, Val Plaisance, N'Géa, Ouémo, Promenade Pierre Vernier.
  - *Nouméa Faubourgs & Centre* : Faubourg Blanchot, Vallée des Colons, Motor Pool, Trianon, Artillerie, Centre-Ville, Vallée du Tir.
  - *Nouméa Nord & Résidentiel* : Haut-Magenta, Magenta, Portes de Fer, Rivière Salée, Ducos (industriel), Tina Golf / Tina Presqu'île (résidentiel).
  - *Agglomération du Grand Nouméa* : Dumbéa (Koutio, Dumbéa-sur-Mer, Auteuil, Val Fleuri), Mont-Dore (Robinson, Boulari, Plum, Yahoué), Païta (Savannah, Beauvallon, Gadji).
  - *Brousse & Îles* : Bourail (Poé, La Roche Percée), La Foa, Koné, Koumac, Île des Pins, Lifou.
- **Foncier & Urbanisme NC** :
  - Référentiel officiel de la **DITTT** (Direction des Infrastructures, de la Topographie et des Transports Terrestres du gouvernement de la Nouvelle-Calédonie).
  - **NIC** : Numéro d'Identification Cadastrale notarié unique (ex: `649536-3794`).
  - **PUD** : Plan d'Urbanisme Directeur fixant les zones (UA centre dense, UB faubourgs résidentiels, UC villas individuelles, etc.), les hauteurs maximales et les emprises au sol.

---

### 2. Architecture des Données & Pipeline ETL

Le projet extrait, agrège, dédoublonne et valorise **2 683 annonces immobilières en direct** à partir de **4 canaux réels majeurs** :
1. **`Immobilier.nc`** : API REST territoriale (702 annonces agences).
2. **`Bienmeloger.nc`** : Flux de syndication d'agences calédoniennes (477 annonces).
3. **`Yatoo.nc`** : API GraphQL native calédonienne (95 annonces particuliers & pros).
4. **`Immo.nc / Immocal`** : Grand portail historique d'annonces indépendant (1 409 annonces extraites via scraper robuste avec pagination et décodage XML/HTML).

#### Schéma ETL :
`src/ingestion/` ➔ `src/processing/` ➔ `src/analysis/` ➔ `src/storage/` ➔ `export_static_data.py`

- **Nettoyage (`ListingCleaner`)** : Distinction stricte entre **Vente** (prix en Millions) et **Location** (loyers mensuels réels), extraction regex des charges copropriété, surfaces habitables, terrains, chambres.
- **Dédoublonnage & Préservation des baisses de prix (`PropertyDatabase`)** :
  - Base de données locale **DuckDB** : `data/processed/immobilier_grand_noumea.duckdb`.
  - Clause `ON CONFLICT (id) DO UPDATE` avec `initial_price_xpf = COALESCE(listings.initial_price_xpf, EXCLUDED.price_xpf)`.
  - **127 baisses de prix réelles sont détectées et historisées** dans la table `listing_price_history`.
- **Moteur Spatial Hybride Cadastre (`src/analysis/cadastre_enrichment.py`)** :
  - `data/cadastre/parcelles_nc.parquet` (77 051 parcelles calédoniennes actives).
  - `data/cadastre/refil_nc.parquet` (3 890 résidences/immeubles répertoriés avec année de construction et adresse).
  - Index spatial 2D par grille projetée pour croiser 2 683 annonces en moins de 0.4 seconde sans base SIG lourde.
  - Résolution d'adresses textuelle REFIL : **777 annonces placées sur leur immeuble exact**.
  - Zéro point dans l'eau ou la mangrove (recalibration des centroïdes côtiers et dispersion sur les vraies parcelles bâties du quartier).

---

### 3. Frontend & Cartographie Haute Performance

- **Interface unique** : [`dashboard_immo_nc.html`](dashboard_immo_nc.html) (et sa copie strictement identique [`index.html`](index.html)).
- **Cartographie Leaflet** :
  - Rendu GPU accéléré via **HTML5 Canvas** (`preferCanvas: true`).
  - Toutes les pastilles de couleur individuelles sont affichées directement à leur adresse sans regroupement masquant :
    🔴 Rouge (>450k F/m² ou >60 MF) • 🟠 Orange (350k - 450k) • 🔵 Bleu Médian • 🟢 Vert Accessible • 🔑 Violet (Locations).
  - Fond de carte **CartoDB Voyager** propulsé par **Fastly Anycast Global CDN** avec mise en cache locale (`keepBuffer: 8`) pour une fluidité totale dans le Pacifique.
  - **Détourage vectoriel de parcelle en direct** :
    - Au clic sur une annonce (ou via le bouton « 🏛️ Détourer Lot »), le client web interroge l'API ArcGIS officielle de `cadastre.gouv.nc` (`MapServer/7/query`).
    - L'API autorise le CORS natif pour `https://hackmachaku.github.io`.
    - Le contour doré vibrant (`#f59e0b`, épaisseur 3.5px, fond ambré translucide) s'affiche instantanément avec centrage et zoom automatique au niveau du lot cadastral (`maxZoom: 18`).
- **Outils Intégrés** :
  - Annuaire des 52 agences partenaires de Nouvelle-Calédonie avec filtres instantanés.
  - Simulateur financier d'investissement locatif (rendement brut, cash-flow mensuel, stress-test de vacance, frais de notaire NC 8%).
  - Moteur d'estimation AVM calédonien avec benchmark par quartier.

---

### 4. Configuration Git & Double Dépôt GitHub

Le projet gère deux dépôts distincts :
1. **Dépôt Principal / Production** :
   - Remote : `origin` ➔ `https://github.com/hackmachaku/immobilier-nc.git`
   - Branche de prod : `main`
   - URL publique GitHub Pages : **https://hackmachaku.github.io/immobilier-nc/**
2. **Dépôt Miroir / Prévisualisation Staging** :
   - Remote : `preview` ➔ `https://github.com/hackmachaku/immobilier-nc-preview.git`
   - Branche de preview : `main` (issue de `feature/cadastre-v2`)
   - URL publique GitHub Pages : **https://hackmachaku.github.io/immobilier-nc-preview/**

---

### 5. Règles Critiques à Respecter Impérativement

1. **Règle de Synchronisation HTML** :
   `dashboard_immo_nc.html` et `index.html` doivent **TOUJOURS** être rigoureusement identiques au caractère près (`(Get-FileHash dashboard_immo_nc.html).Hash -eq (Get-FileHash index.html).Hash` doit renvoyer `True`).
2. **Accès Concurrence DuckDB** :
   Sur Windows, pour toute requête de lecture, DuckDB doit impérativement être instancié avec `PropertyDatabase(read_only=True)` afin d'éviter tout conflit de verrouillage de fichier (`IO Error: Cannot open file ... utilisé par un autre processus`).
3. **Validation par les Tests** :
   Avant toute modification majeure, la suite de tests automatisée doit être exécutée avec `pytest tests/ -q` et afficher **42 tests passés avec succès**.
4. **Gestion des Dépôts** :
   Ne jamais écraser `origin/main` sans confirmation explicite. Tester d'abord sur `preview` ou sur une branche dédiée.

---

### 6. Commandes Utiles de Démarrage

- **Activer l'environnement virtuel** : `.\.venv\Scripts\activate` (ou `source .venv/bin/activate`)
- **Lancer le serveur local** : `python server.py` (accessible sur `http://localhost:8080`)
- **Lancer les tests** : `pytest tests/ -q`
- **Régénérer les snapshots JSON** : `python export_static_data.py`
- **Empaqueter une migration** : `python scripts/package_migration.py`

Tu es maintenant prêt à poursuivre nos travaux. Confirme-moi que tu as bien intégré l'architecture et demande-moi ce que nous faisons aujourd'hui !
```
