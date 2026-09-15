# 📦 Guide de Migration Complète • Immobilier NC Sentinel

Ce document explique pas-à-pas comment transférer et faire tourner l'intégralité du projet **Veille Immo NC Sentinel** sur un nouvel ordinateur (Windows, macOS ou Linux) en moins de 5 minutes.

---

## 📋 Méthodes de Transfert Disponibles

Vous avez le choix entre **deux méthodes** pour transférer le projet :

### Méthode 1 : Clone depuis GitHub (Recommandé si vous avez une bonne connexion)
Le code, les tests, la base DuckDB et les snapshots de données sont hébergés sur GitHub.
```bash
git clone https://github.com/hackmachaku/immobilier-nc.git
cd immobilier-nc
```
*Note : Si vous souhaitez également avoir la branche de prévisualisation avec les parquets cadastre :*
```bash
git checkout feature/cadastre-v2
```

### Méthode 2 : Archive ZIP Complète Clé en Main (100% Hors-ligne avec tout l'historique brut)
Si vous disposez de l'archive ZIP générée sur l'ancien ordinateur (`migration_bundle_immobilier_nc.zip`) :
1. Copiez le fichier ZIP sur votre nouvel ordinateur (via clé USB, disque externe ou Cloud Drive).
2. Décompressez l'archive dans le dossier de votre choix (ex: `C:\Projets\Immobilier NC`).
3. Ouvrez un terminal (PowerShell ou Bash) dans ce dossier.

---

## 🚀 Installation & Démarrage sur le Nouvel Ordinateur

### 1. Prérequis Système
- **Python 3.10, 3.11 ou 3.12+** installé ([Télécharger Python](https://www.python.org/downloads/)).
  *⚠️ Lors de l'installation sur Windows, cochez impérativement la case **« Add Python to PATH »**.*
- **Git** installé ([Télécharger Git](https://git-scm.com/)).

---

### 2. Création de l'Environnement Virtuel & Dépendances

Ouvrez votre terminal dans le dossier du projet :

#### Sous Windows (PowerShell) :
```powershell
# 1. Création de l'environnement virtuel
python -m venv .venv

# 2. Activation de l'environnement
.\.venv\Scripts\Activate.ps1
# (Si PowerShell bloque l'activation : Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# 3. Mise à jour de pip et installation des packages
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Sous macOS / Linux (Terminal) :
```bash
# 1. Création de l'environnement virtuel
python3 -m venv .venv

# 2. Activation de l'environnement
source .venv/bin/activate

# 3. Installation des dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 3. Validation de l'Installation (Tests Automatisés)

Avant de lancer le serveur, exécutez la suite de tests pour vous assurer que tout est opérationnel :
```bash
pytest tests/ -q
```
*Résultat attendu : `42 passed` (100% de succès).*

---

### 4. Lancement du Serveur & Dashboard Local

#### Option A : En ligne de commande
```bash
python server.py
```
Le serveur démarre immédiatement. Ouvrez votre navigateur web sur :  
👉 **[http://localhost:8080](http://localhost:8080)**

#### Option B : Double-clic Windows
Double-cliquez simplement sur le fichier :
- **`lancer_interface_web.bat`** : Lance le serveur en arrière-plan et ouvre automatiquement votre navigateur sur le dashboard.
- **`lancer_pipeline_complet.bat`** : Exécute le pipeline complet (scraping, nettoyage, enrichissement DuckDB et export statique).

---

## 🔗 Configuration des Dépôts Distants Git (Dual-Repo)

Si vous souhaitez continuer à pousser sur les deux dépôts GitHub créés :

```bash
# Vérifier les remotes existants
git remote -v

# Si le remote de preview n'est pas configuré, ajoutez-le :
git remote add preview https://github.com/hackmachaku/immobilier-nc-preview.git

# Mettre à jour la production (dépôt principal) :
git push origin main

# Mettre à jour la prévisualisation (dépôt preview) :
git push preview feature/cadastre-v2:main
```

---

## 🧠 Transmission à une IA sur le Nouveau PC

Dès que vous ouvrez le projet dans votre éditeur (VS Code, Antigravity, Cursor) sur la nouvelle machine, ouvrez le fichier :  
📄 **[`HANDOVER_AI_PROMPT.md`](file:///c:/Users/WD4060/OneDrive%20-%20ENGIE/Documents/Antigravity/Immobilier%20NC/HANDOVER_AI_PROMPT.md)**

Copiez et collez l'intégralité de son contenu dans votre premier message à l'assistant IA. Il comprendra instantanément 100% de l'architecture, des spécificités calédoniennes, des tâches accomplies et pourra poursuivre le travail sans aucune perte de contexte !
