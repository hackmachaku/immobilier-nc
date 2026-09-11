# 🏛️ Réseau des 52 Agences Immobilières Calédoniennes

En Nouvelle-Calédonie, le marché de la transaction et de la gestion locative est structuré autour d'une cinquantaine d'agences historiques et de cabinets indépendants.

---

## 1. Principe de Fonctionnement & Syndication

La quasi-totalité des agences immobilières en Nouvelle-Calédonie utilise des logiciels de gestion de mandats professionnels (*Transellis, Netty, Apimo*).

Plutôt que d'obliger chaque agence à maintenir une API publique distincte, notre robot d'ingestion interroge les flux territoriaux consolidés (*Immobilier.nc, Bienmeloger.nc*) et résout automatiquement l'agence propriétaire via :
1. L'e-mail du négociateur (`owner.mail`).
2. Le nom complet du négociateur (`owner.full_name`).
3. Le texte de description de l'annonce et les mentions légales.

---

## 2. Tableau des Agences Référencées

L'annuaire complet est intégré dans [`src/domain/agencies_directory.py`](https://github.com/hackmachaku/immobilier-nc/blob/main/src/domain/agencies_directory.py) et comprend notamment :

| Agence Partenaire | Commune Principale | Site Web Officiel |
| :--- | :--- | :--- |
| **L'Agence Générale** | Nouméa | [agencegenerale.nc](https://www.agencegenerale.nc) |
| **Bien-Immo** | Nouméa | [bien-immo.nc](https://www.bien-immo.nc) |
| **Ellipse Immo** | Koné / Nord | [ellipseimmo.nc](https://www.ellipseimmo.nc) |
| **Caillard & Kaddour** | Nouméa | [caillard-kaddour.com](https://www.caillard-kaddour.com) |
| **Acti Immobilier** | Nouméa | [acti-immo.nc](https://www.acti-immo.nc) |
| **Agence Soleil** | Nouméa | [soleil.nc](https://www.soleil.nc) |
| **Cabinet Lacroix** | Nouméa | [lacroix-immobilier.nc](https://www.lacroix-immobilier.nc) |
| **Top Immo** | Nouméa / Dumbéa | [topimmo.nc](https://www.topimmo.nc) |
| **Open Immobilier** | Nouméa | [open-immobilier.nc](https://www.open-immobilier.nc) |
| **SIC (Bailleur Social NC)** | Nouméa | [sic.nc](https://www.sic.nc) |
| **Investiss' Immo** | Nouméa | [investiss-immo.nc](https://www.investiss-immo.nc) |
| **Alert'Immo** | Nouméa | [alertimmo.nc](https://alertimmo.nc) |
| **Chatelin Immobilier** | Nouméa | [chatelin-immobilier.nc](https://www.chatelin-immobilier.nc) |
| **Immonord** | Poindimié / Nord | [immonord.nc](https://www.immonord.nc) |
| **Diot Immobilier** | Nouméa | [diot-immobilier.nc](https://www.diot-immobilier.nc) |
| **Nouméa Immobilier** | Nouméa | [noumeaimmobilier.nc](https://www.noumeaimmobilier.nc) |
| **Promobat** | Nouméa | [promobat.nc](https://www.promobat.nc) |
| *(et plus de 35 autres agences calédoniennes)* | — | — |

---

## 3. Accès Direct aux Mandats par Agence

Dans l'application :
- Rendez-vous dans l'onglet **Paramètres / Sources**.
- Dans le tableau **Réseau des 52 Agences**, cliquez sur **`👁️ Voir annonces (N)`** pour afficher instantanément la sélection complète des biens de cette agence.
