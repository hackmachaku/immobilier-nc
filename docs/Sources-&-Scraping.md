# 🛰️ Sources de Données & Moteur de Collecte (Scraping)

Ce document décrit le fonctionnement des flux de données et des connecteurs automatisés.

---

## 1. Portails et Flux Intégrés

### A. Immobilier.nc & Bienmeloger.nc (API REST Directe)
- **Endpoint principal** : `https://api.immobilier.nc/api/posts`
- **Paramètres de pagination** :
  - Ventes : `?by_deal_type=vente&scope=offers&page=N` (plus de 3 300 annonces réelles actives)
  - Locations : `?by_deal_type=location&scope=offers&page=N` (plus de 3 000 annonces locatives actives)
- **Données extraites** : Titre, prix, type de bien, commune, quartier, surface habitable, surface terrain, photos originales hébergées sur `gestion.immobilier.nc` ou `bienmeloger.nc/media/`.

### B. Yatoo.nc (API GraphQL Native)
- **Endpoint Cloud Function** : `https://australia-southeast1-yatoo-nc.cloudfunctions.net/api`
- **Opération** : `getSearchPosts`
- **Catégories surveillées** :
  - `ventes-immobilieres`
  - `locations`
- **Images** : Photos réelles stockées sur Google Cloud Storage (`storage.googleapis.com/yatoo-nc-bucket-2021/`).

---

## 2. Déclenchement & Actualisation Forcée

Dans l'interface web (onglet Sources) :
- Le bouton **`🔄 Forcer l'actualisation des sources`** permet de relancer un scan multi-pages en direct (de 125 à 1 000 annonces).
- Une barre de progression en temps réel affiche le téléchargement des pages, la normalisation ETL et l'enregistrement dans la base DuckDB locale.

---

## 3. Contrôle d'Intégrité & Audit (PipelineAuditor)

Un système d'audit intégré vérifie après chaque synchronisation :
1. **Intégrité de la base DuckDB** :
   - Présence de prix valides (`null_prices == 0`).
   - Taux de surfaces exploitables (`valid_m2_ratio_pct >= 65%`).
   - Bon fonctionnement des vues SQL d'analyse de marché (`v_marche_par_quartier`, `v_marche_par_typologie`).
2. **Journal d'exécution** :
   - Analyse des logs `logs/pipeline.log`.
   - Décompte des erreurs (Statut `HEALTHY` avec 0 erreur).
