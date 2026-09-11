# 🏝️ Bienvenue sur le Wiki de Veille Immo NC Sentinel

Bienvenue sur la documentation officielle de **Veille Immo NC Sentinel**, l'observatoire et moteur d'intelligence immobilière de référence en Nouvelle-Calédonie.

Ce projet agrège, nettoie et analyse en continu le marché immobilier calédonien (Grand Nouméa et Brousse) pour offrir une vision exhaustive et en temps réel des offres à la vente et à la location.

---

## 🌐 Liens Rapides

- **Application en ligne** : [https://hackmachaku.github.io/immobilier-nc/](https://hackmachaku.github.io/immobilier-nc/)
- **Dépôt GitHub** : [https://github.com/hackmachaku/immobilier-nc](https://github.com/hackmachaku/immobilier-nc)

---

## 📚 Sommaire du Wiki

1. [[Guide Utilisateur]]
   - Prise en main du tableau de bord
   - Recherche par mots-clés et filtres avancés
   - Fiches d'annonces détaillées et leviers de négociation
   - Simulateurs AVM et Rentabilité Locative

2. [[Réseau des 52 Agences]]
   - Annuaire officiel des 52 agences partenaires en Nouvelle-Calédonie
   - Modèle de syndication (Transellis, Netty, Apimo)
   - Filtrage et contact direct des agences

3. [[Sources & Scraping]]
   - Flux d'ingestion en direct : *Immobilier.nc*, *Bienmeloger.nc*, *Yatoo.nc*
   - Mécanisme d'actualisation forcée et pagination
   - Journalisation, monitoring et audit d'intégrité DuckDB

4. [[Architecture Technique]]
   - Stack technologique : Python 3.12, DuckDB, Leaflet, Tailwind CSS
   - Modèle de données normalisé et typologies calédoniennes
   - Pipeline ETL (Clean > Enrich > Store)
