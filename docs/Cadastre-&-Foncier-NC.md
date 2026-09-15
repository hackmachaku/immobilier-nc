# 🏛️ Guide Foncier, Cadastre & Urbanisme de Nouvelle-Calédonie

Ce document détaille le fonctionnement du moteur spatial cadastral intégré à la plateforme **Veille Immo NC Sentinel**, ainsi que les sources de données officielles du gouvernement de la Nouvelle-Calédonie (DITTT).

---

## 1. Données Cadastrales Officielles Utilisées

La plateforme exploite les données officielles publiées par la **Direction des Infrastructures, de la Topographie et des Transports Terrestres (DITTT)** de Nouvelle-Calédonie et le service **cadastre.gouv.nc** :

### 1. `parcelles_nc.parquet` (4.8 Mo - 77 051 parcelles actives)
Contient l'ensemble du découpage parcellaire officiel de Nouvelle-Calédonie :
- **NIC (Numéro d'Identification Cadastrale)** : Identifiant notarié unique national (ex: `649536-3794`).
- **Lot Géomètre & Lotissement** : Numéro officiel de lot cadastral et nom du lotissement d'origine (ex: *Lot 17, Lotissement Flamboyant*).
- **Commune & Section Cadastrale** : Rattachement administratif officiel.
- **Contenance Légale Notariée** : Surface officielle en format notarié (`hectares, ares, centiares`) et conversion automatique en mètres carrés (`m²`).
- **Typologie Foncière** : Propriété privée, domaine public communal, domaine territorial ou provincial.

### 2. `refil_nc.parquet` (454 Ko - 3 890 ensembles bâtis et résidences)
Répertoire des ensembles immobiliers et copropriétés du Grand Nouméa (REFIL) :
- **Nom officiel de la résidence / de l'immeuble** (ex: *Tour Isle de France*, *Résidence Le Bellagio*, *Résidence Port Moselle*).
- **Année ou date officielle de livraison/construction**.
- **Adresse postale normalisée**.
- **Type de gestion** (Privé, Copropriété, Société Immobilière Calédonienne SIC, FSH).

---

## 2. Algorithmes Métier & Moteur Spatial Hybride

### Index Spatial Grille 2D (`CadastreSpatialIndex`)
Implémenté dans [`src/analysis/cadastre_enrichment.py`](../src/analysis/cadastre_enrichment.py) :
- Permet d'indexer 77 051 parcelles et 3 890 résidences en mémoire en **0.3 seconde**.
- Utilise une grille de coordonnées géographiques avec projection équirectangulaire calédonienne (`cos(-22.25°)`).
- Résout la parcelle la plus proche en moins de **0.2 milliseconde** par annonce sans base de données spatiale externe (PostGIS).

### Résolution Textuelle REFIL
- Détection par expressions régulières et correspondances sémantiques des noms de résidences dans les titres et descriptions des annonces.
- Permet de localiser précisément **777 appartements** sur leur emprise exacte au mètre près, même lorsque l'annonce omet le numéro de rue.

### Détection des Écarts de Surface
- Compare la surface habitable / terrain déclarée dans l'annonce avec la contenance légale notariée issue du cadastre.
- **Maisons et Terrains** :
  - Écart `< 5%` : ✅ Surface Conforme.
  - Écart `5% à 15%` : ℹ️ Écart mineur acceptable.
  - Écart `> 15%` : ⚠️ Alerte écart significatif notifié à l'acheteur.
- **Appartements & Copropriétés** :
  - Détection automatique de l'**assiette foncière de copropriété** pour éviter les faux positifs (ex: un appartement de 75 m² sur une parcelle globale de 1 200 m²).

---

## 3. Détourage Vectoriel Polygonal en Direct (ArcGIS)

Lorsqu'un utilisateur sélectionne une annonce sur la carte ou clique sur **« 🏛️ Détourer Lot »** :

1. **Requête API ArcGIS MapServer 7** :
   ```
   https://cadastre.gouv.nc/arcgisServices/cadastreV3/cadastre_consult_v333/MapServer/7/query?geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=true&outSR=4326&f=json
   ```
2. **Compatibilité CORS Totale** :
   Le serveur de `cadastre.gouv.nc` autorise nativement les requêtes d'origine `https://hackmachaku.github.io`, permettant au contour vectoriel de s'afficher instantanément aussi bien en local que sur GitHub Pages.
3. **Rendu Leaflet** :
   - Conversion des anneaux Esri (`rings`) en polygone GeoJSON.
   - Tracé couleur Or / Ambre vibrant (`#f59e0b`, fond ambré translucide).
   - Zoom et centrage automatique précis sur la parcelle via `map.flyToBounds(bounds, { maxZoom: 18 })`.

---

## 4. Règles d'Urbanisme PUD (Plan d'Urbanisme Directeur)

La plateforme intègre les zonages et règlements du PUD des communes du Grand Nouméa (Nouméa, Dumbéa, Mont-Dore, Païta) :

| Zone PUD | Vocation Principale | Hauteur Maximale | Emprise au Sol | Droits & Règles Notables |
| :--- | :--- | :--- | :--- | :--- |
| **UA** | Centre-Ville & Mixité dense | R+6 à R+10 (32 m) | 80% à 100% | Forte constructibilité, commerces et bureaux autorisés |
| **UB** | Faubourgs denses & Balnéaire | R+3 / R+4 (12 à 15 m) | 45% à 50% | Résidentiel intermédiaire, villas et petits collectifs |
| **UC** | Résidentiel pavillonnaire | R+1 + combles (7 à 9 m) | 30% à 40% | Villas individuelles, espaces verts obligatoires |
| **UD / UZ** | Zones d'aménagement concerté | Selon cahier des charges | 40% | Lotissements résidentiels récents |
| **I / UI** | Zones industrielles (Ducos) | R+2 (12 m) | 60% à 70% | Docks, ateliers, commerces de gros |
