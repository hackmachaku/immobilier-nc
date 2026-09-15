# 🏝️ Veille Immo NC Sentinel • Observatoire Immobilier de Nouvelle-Calédonie

Plateforme d'intelligence de marché, de veille continue, d'estimation et d'analyse cadastrale pour l'immobilier en **Nouvelle-Calédonie (Grand Nouméa et Brousse)**.

| Environnement | Statut | URL Publique (GitHub Pages) | Dépôt GitHub |
| :--- | :--- | :--- | :--- |
| **Production** | 🟢 En ligne | [https://hackmachaku.github.io/immobilier-nc/](https://hackmachaku.github.io/immobilier-nc/) | [`hackmachaku/immobilier-nc`](https://github.com/hackmachaku/immobilier-nc) |
| **Preview Staging (Cadastre & Haute Précision)** | 🧪 En ligne | [https://hackmachaku.github.io/immobilier-nc-preview/](https://hackmachaku.github.io/immobilier-nc-preview/) | [`hackmachaku/immobilier-nc-preview`](https://github.com/hackmachaku/immobilier-nc-preview) |

---

## 🌟 Fonctionnalités Clés

- **🛰️ Agrégation Multi-Sources en Direct (2 683 annonces réelles)** :
  - **`Immobilier.nc`** : API REST territoriale (702 annonces agences).
  - **`Bienmeloger.nc`** : Flux de syndication professionnelle (477 annonces).
  - **`Yatoo.nc`** : API GraphQL native (95 annonces pros & particuliers).
  - **`Immo.nc / Immocal`** : Grand portail historique calédonien (1 409 annonces via scraper résilient).
- **📉 Détecteur Intelligent de Baisses de Prix** :
  - Historisation chronologique des variations de prix dans DuckDB (`initial_price_xpf` préservé).
  - **127 baisses de prix réelles identifiées** avec filtre direct, badges d'économies et timeline chronologique.
- **🏛️ Enrichissement Foncier, Cadastral & Urbanisme Officiel (DITTT)** :
  - Intégration de la base officielle des **77 051 parcelles de Nouvelle-Calédonie** :
    - Numéro d'Identification Cadastrale unique notarié (**NIC**).
    - Numéro de **Lot géomètre** & Nom du **Lotissement**.
    - **Contenance légale notariée** (hectares, ares, centiares convertis en m²).
  - Répertoire **REFIL de 3 890 résidences / immeubles** avec année de construction et adresse normalisée.
  - **Détourage polygonal vectoriel en direct** : au clic sur un bien, interrogation directe de l'API ArcGIS officielle de `cadastre.gouv.nc` (`MapServer/7/query`) avec tracé doré ultra-net et zoom automatique sur le lot.
  - Consultation instantanée des règles de zone du **PUD communal** (UA, UB, UC, hauteurs maximales et emprises au sol).
- **🗺️ Cartographie Haute Performance (60 FPS GPU)** :
  - Rendu direct sur HTML5 Canvas via Leaflet (`preferCanvas: true`).
  - Toutes les annonces sont positionnées individuellement avec leur pastille de couleur réelle sans masquage :
    🔴 Prestige (>450k F/m²) • 🟠 Supérieur (350k - 450k) • 🔵 Médian • 🟢 Accessible (<250k) • 🔑 Locations.
  - Fond de carte **CartoDB Voyager** propulsé par **Fastly Anycast Global CDN** avec cache local (`keepBuffer: 8`) pour un chargement instantané dans la région Pacifique.
- **🏢 Réseau des 52 Agences Immobilières Calédoniennes** :
  - Annuaire complet avec contacts directs, décompte en direct des mandats et filtre agences / particuliers.
- **📈 Simulateur de Rendement Locatif & Moteur AVM** :
  - Calcul de cash-flow mensuel, taux d'emprunt, frais de notaire NC (8%) et stress-test de vacance locative.

---

## 🚀 Démarrage Rapide en Local

### 1. Prérequis
- Python 3.10, 3.11 ou 3.12+
- Git

### 2. Installation
```bash
git clone https://github.com/hackmachaku/immobilier-nc.git
cd immobilier-nc

# Créer et activer l'environnement virtuel
python -m venv .venv
.\.venv\Scripts\activate   # Sous Windows
# source .venv/bin/activate # Sous macOS / Linux

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Lancement du Serveur
```bash
python server.py
```
Ouvrez votre navigateur sur : **[http://localhost:8080](http://localhost:8080)**

*(Sous Windows, vous pouvez également double-cliquer directement sur `lancer_interface_web.bat`).*

---

## 🧪 Tests Automatisés

La suite de tests garantit le non-régression de l'ingestion, du nettoyage des prix, de l'enrichissement cadastral et de l'intégrité de la base DuckDB :
```bash
pytest tests/ -q
```
*Résultat : **42 tests passés avec succès (100%)**.*

---

## 📦 Migration vers un Nouvel Ordinateur

Si vous transférez ce projet sur une nouvelle machine :
1. Consultez le guide détaillé : **[`MIGRATION.md`](MIGRATION.md)**.
2. Pour transmettre l'intégralité du contexte à une IA sur le nouveau poste, utilisez : **[`HANDOVER_AI_PROMPT.md`](HANDOVER_AI_PROMPT.md)**.
3. Pour générer une archive ZIP complète autonome :
   ```bash
   python scripts/package_migration.py
   ```

---

## 📚 Documentation Détaillée

- 📖 **[[Guide Utilisateur|docs/Guide-Utilisateur.md]]**
- 🏛️ **[[Cadastre & Foncier DITTT|docs/Cadastre-&-Foncier-NC.md]]**
- 🏢 **[[Réseau des 52 Agences|docs/Reseau-des-52-Agences.md]]**
- 🛰️ **[[Sources & Scraping|docs/Sources-&-Scraping.md]]**
- 🛠️ **[[Architecture Technique & DuckDB|docs/Architecture-Technique.md]]**

---

*Développé avec Antigravity pour le marché immobilier de Nouvelle-Calédonie.*
