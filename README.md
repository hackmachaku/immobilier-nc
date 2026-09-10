# 🏝️ Veille Immo NC Sentinel • Observatoire Immobilier de Nouvelle-Calédonie

Plateforme intelligente de veille, d'estimation et d'analyse du marché immobilier en Nouvelle-Calédonie (Grand Nouméa & Brousse).

🌐 **Site en ligne (GitHub Pages)** : [https://hackmachaku.github.io/immobilier-nc/](https://hackmachaku.github.io/immobilier-nc/)

---

## 🌟 Fonctionnalités Principales

- **🛰️ Agrégation Multi-Sources en Direct** :
  - `Immobilier.nc` (API REST territoriale)
  - `Bienmeloger.nc` (Flux d'annonces calédoniennes)
  - `Yatoo.nc` (API GraphQL native)
  - Passerelles de syndication professionnelles (*Transellis, Netty, Apimo*).
- **🏛️ Réseau des 52 Agences Immobilières Calédoniennes** :
  - Répertoire complet des agences avec sites officiels, contacts et décompte en direct des mandats (ventes & locations).
  - Filtre par agence ou pour isoler les vendeurs particuliers.
- **🏡 Ventes & 🔑 Locations Différenciées** :
  - Prix de vente en Millions F CFP et loyers mensuels réels avec ratios m².
  - Photos authentiques haute définition et liens directs vers les annonces sources.
- **🧠 Diagnostic Économique & Analyse de Négociation (IA)** :
  - Évaluation de tension de marché, détection d'opportunités, calcul de décote et fourchettes de négociation recommandées.
- **🗺️ Cartographie Interactive Leaflet** :
  - Carte thermique des prix au m² par quartier (Anse Vata, Baie des Citrons, Val Plaisance, Savannah, Robinson, Dumbéa, etc.).
- **📈 Simulateur de Rendement & Cash-Flow** :
  - Simulation bancaire, calcul d'emprunt, charges calédoniennes et stress-test de vacance locative.

---

## 🚀 Démarrage en Local

### 1. Prérequis
- Python 3.10+
- Navigateur moderne (Chrome, Edge, Firefox, Safari)

### 2. Installation
```bash
git clone https://github.com/hackmachaku/immobilier-nc.git
cd immobilier-nc
python -m venv .venv
source .venv/bin/activate  # Sous Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Lancement du Serveur & Dashboard
```bash
python server.py
```
Ouvrez votre navigateur sur : [http://localhost:8080](http://localhost:8080)

---

## 🧪 Tests Automatisés
```bash
pytest tests/
```

---

*Développé avec Antigravity pour le marché immobilier de Nouvelle-Calédonie.*
