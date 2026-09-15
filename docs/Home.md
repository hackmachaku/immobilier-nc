# 🏝️ Bienvenue sur le Wiki de Veille Immo NC Sentinel

Bienvenue sur la documentation officielle de **Veille Immo NC Sentinel**, l'observatoire et moteur d'intelligence immobilière de référence en Nouvelle-Calédonie.

Ce projet agrège, nettoie, enrichit et analyse en continu le marché immobilier calédonien (Grand Nouméa et Brousse) pour offrir une vision exhaustive et en temps réel de **2 683 offres actives** à la vente et à la location.

---

## 🌐 Liens Rapides

- **Site de Production (Stable)** : [https://hackmachaku.github.io/immobilier-nc/](https://hackmachaku.github.io/immobilier-nc/)
- **Site de Prévisualisation (Cadastre & Haute Précision)** : [https://hackmachaku.github.io/immobilier-nc-preview/](https://hackmachaku.github.io/immobilier-nc-preview/)
- **Dépôt Principal** : [https://github.com/hackmachaku/immobilier-nc](https://github.com/hackmachaku/immobilier-nc)
- **Dépôt Preview** : [https://github.com/hackmachaku/immobilier-nc-preview](https://github.com/hackmachaku/immobilier-nc-preview)

---

## 📚 Sommaire de la Documentation

1. [[Guide-Utilisateur|Guide Utilisateur]]
   - Prise en main du tableau de bord
   - Recherche par mots-clés et filtres avancés (Ventes, Locations, Baisses de prix)
   - Fiches d'annonces détaillées, photos et leviers de négociation IA
   - Simulateurs AVM et Rentabilité Locative Calédonienne

2. [[Cadastre-&-Foncier-NC|Cadastre, Foncier & Urbanisme (DITTT)]]
   - Base officielle des 77 051 parcelles de Nouvelle-Calédonie (NIC, Lot, Contenance notariée)
   - Répertoire REFIL des 3 890 résidences avec année de construction
   - Moteur spatial hybride 2D ultra-rapide (0.3 seconde)
   - Détourage vectoriel polygonal en direct via l'API ArcGIS `cadastre.gouv.nc`
   - Règles d'urbanisme PUD (UA, UB, UC, hauteurs max et droits à bâtir)

3. [[Reseau-des-52-Agences|Réseau des 52 Agences]]
   - Annuaire officiel des 52 agences partenaires en Nouvelle-Calédonie
   - Modèle de syndication (Transellis, Netty, Apimo)
   - Décompte réel des mandats et filtrage par agence ou particuliers

4. [[Sources-&-Scraping|Sources & Scraping (4 Canaux Réels)]]
   - Flux d'ingestion en direct : *Immobilier.nc*, *Bienmeloger.nc*, *Yatoo.nc*, *Immo.nc / Immocal*
   - Mécanisme d'actualisation forcée et pagination multi-pages
   - Journalisation, monitoring et audit d'intégrité DuckDB

5. [[Architecture-Technique|Architecture Technique & Schéma DuckDB]]
   - Stack technologique : Python 3.12, DuckDB, Leaflet Canvas GPU, Tailwind CSS
   - Schéma relationnel `listings` et `listing_price_history` (127 baisses de prix)
   - Pipeline ETL (Ingestion > Nettoyage > Spatial > Stockage > Export Statique)
