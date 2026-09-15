# 🛰️ Sources de Données & Moteur de Collecte (Scraping) • Veille Immo NC Sentinel

Ce document décrit le fonctionnement des flux de données, des connecteurs API et des scrapers automatisés intégrés à la plateforme.

---

## 1. Portails et Flux Intégrés (4 Canaux Réels)

La plateforme surveille et agrège en direct **2 683 annonces réelles** en Nouvelle-Calédonie à travers 4 canaux majeurs :

| Source | Type de Connexion | Volume Actif Réel | Spécificités & Rôle |
| :--- | :--- | :--- | :--- |
| **Immobilier.nc** | API REST Directe | 702 annonces | Portail fédérateur des 52 agences calédoniennes |
| **Bienmeloger.nc** | API REST & Syndication | 477 annonces | Passerelle CRM professionnelle (Netty, Apimo) |
| **Yatoo.nc** | API GraphQL Native | 95 annonces | Plateforme locale d'annonces de particuliers & indépendants |
| **Immo.nc / Immocal** | Scraper Web HTTP Direct | 1 409 annonces | Portail historique d'annonces agences & particuliers |

---

## 2. Détail Technique des Connecteurs

### A. Immobilier.nc & Bienmeloger.nc (API REST)
- **Endpoint principal** : `https://api.immobilier.nc/api/posts`
- **Paramètres de pagination** :
  - Ventes : `?by_deal_type=vente&scope=offers&page=N`
  - Locations : `?by_deal_type=location&scope=offers&page=N`
- **Champs collectés** : ID annonce, titre, deal_type, catégorie, commune, quartier, prix XPF, surface habitable, surface terrain, photos originales hébergées sur `gestion.immobilier.nc` ou `bienmeloger.nc/media/`.

### B. Yatoo.nc (API GraphQL)
- **Endpoint Cloud Function** : `https://australia-southeast1-yatoo-nc.cloudfunctions.net/api`
- **Opération GraphQL** : `getSearchPosts`
- **Catégories surveillées** : `ventes-immobilieres`, `locations`
- **Stockage images** : Bucket Google Cloud Storage officiel (`storage.googleapis.com/yatoo-nc-bucket-2021/`).

### C. Immo.nc / Immocal (Connecteur Scraping Robuste)
- **URL racine** : `https://www.immonc.com/`
- **Pages ciblées** :
  - Ventes : `https://www.immonc.com/annonces/ventes/` (avec pagination `?page=N`)
  - Locations : `https://www.immonc.com/annonces/locations/` (avec pagination `?page=N`)
- **Moteur d'extraction** :
  - Analyse des flux HTML/XML avec expressions régulières et parsers résilients.
  - Détection automatique des identifiants uniques calédoniens (`immonc_XXXXXX`).
  - Extraction de la date de publication, de l'agence mandataire (ou Particulier), des prix, surfaces, photos haute définition.
  - Temporisation adaptative anti-blocage (gestion des User-Agents et respect des serveurs locaux).

---

## 3. Déclenchement & Synchronisation en Direct

Dans l'interface web (onglet **Sources**) :
- Le bouton **`🔄 Forcer l'actualisation des sources`** déclenche un scan réel multi-sources (volume paramétrable de 3 à 20 pages).
- L'appel POST `/api/refresh` exécute le pipeline ETL, met à jour la base DuckDB locale et rafraîchit instantanément l'affichage du dashboard.
- Un bouton d'actualisation unitaire permet également de relancer le scan d'un canal spécifique (ex: uniquement Yatoo ou Immo.nc).

---

## 4. Contrôle d'Intégrité & Audit (PipelineAuditor)

Après chaque synchronisation, un audit automatique valide :
1. **Intégrité des données DuckDB** :
   - Présence de prix valides (`null_prices == 0`).
   - Ratio de surfaces exploitables (`valid_m2_ratio_pct >= 65%`).
   - Préservation des baisses de prix constatées (`initial_price_xpf` conservé lors des mises à jour).
2. **Audit du journal des logs** :
   - Analyse de `logs/pipeline.log`.
   - Rapport JSON généré dans `logs/audit_report.json` avec statut `HEALTHY`.
