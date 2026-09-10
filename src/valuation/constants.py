"""
Constantes, barèmes territoriaux et coefficients hédoniques d'évaluation immobilière
pour le Grand Nouméa (Nouméa, Dumbéa, Mont-Dore, Païta).
"""

from typing import Dict, Tuple
from src.models.listing import Commune, PropertyType

# ==============================================================================
# 1. PRIX DE BASE AU M² HABITABLE (F CFP / XPF) PAR QUARTIER ET TYPE DE BIEN
# Ces barèmes reflètent l'état actuel du marché néo-calédonien post-2024.
# ==============================================================================

# Structure : { Commune: { Quartier: (prix_m2_appartement, prix_m2_maison_villa) } }
PRIX_BASE_M2_QUARTIER: Dict[Commune, Dict[str, Tuple[int, int]]] = {
    Commune.NOUMEA: {
        "Anse Vata": (550_000, 520_000),
        "Baie des Citrons": (540_000, 500_000),
        "Val Plaisance": (510_000, 480_000),
        "Ouémo": (520_000, 490_000),
        "N'Géa": (500_000, 470_000),
        "Tuband": (480_000, 460_000),
        "Port Plaisance": (490_000, 460_000),
        "Artillerie": (450_000, 430_000),
        "Motor Pool": (420_000, 400_000),
        "Trianon": (410_000, 390_000),
        "Faubourg Blanchot": (430_000, 410_000),
        "Vallée des Colons": (400_000, 380_000),
        "Magenta": (370_000, 350_000),
        "Tina": (440_000, 420_000),
        "Centre-Ville": (350_000, 330_000),
        "Vallée du Tir": (320_000, 300_000),
        "Rivière Salée": (280_000, 260_000),
        "Ducos": (260_000, 250_000),
        "Normandie": (290_000, 270_000),
    },
    Commune.DUMBEA: {
        "Dumbéa-sur-Mer": (320_000, 300_000),
        "Koutio": (300_000, 280_000),
        "Auteuil": (290_000, 270_000),
        "Katiramona": (270_000, 260_000),
        "Nondoué": (260_000, 250_000),
        "Nakutakoin": (270_000, 260_000),
    },
    Commune.PAITA: {
        "Savannah": (380_000, 370_000),
        "Beauvallon": (310_000, 295_000),
        "Val Boisé": (300_000, 285_000),
        "Païta Village / Centre": (280_000, 270_000),
        "Gadji": (290_000, 275_000),
        "Mont-Mou": (270_000, 260_000),
    },
    Commune.MONT_DORE: {
        "Pont-des-Français": (330_000, 310_000),
        "Conception": (340_000, 320_000),
        "Robinson": (330_000, 315_000),
        "Boulari": (340_000, 310_000),
        "Saint-Michel": (300_000, 280_000),
        "Vallon-Dore": (290_000, 270_000),
        "La Coulée": (270_000, 250_000),
        "Plum": (250_000, 230_000),
    },
}

# Prix moyen par défaut au m² par commune en cas de quartier non répertorié
PRIX_DEFAUT_COMMUNE: Dict[Commune, Tuple[int, int]] = {
    Commune.NOUMEA: (420_000, 400_000),
    Commune.DUMBEA: (290_000, 275_000),
    Commune.PAITA: (300_000, 285_000),
    Commune.MONT_DORE: (310_000, 290_000),
    Commune.AUTRE: (280_000, 260_000),
}

# ==============================================================================
# 2. VALORISATION DU TERRAIN RÉSIDUEL (F CFP / m²) POUR LES VILLAS
# ==============================================================================
PRIX_M2_TERRAIN_PAR_COMMUNE: Dict[Commune, int] = {
    Commune.NOUMEA: 35_000,     # Foncier rare à Nouméa
    Commune.PAITA: 15_000,      # Grands terrains (Savannah, etc.)
    Commune.MONT_DORE: 12_000,  # Terrains de 8 à 15 ares
    Commune.DUMBEA: 14_000,     # Périurbain dense
    Commune.AUTRE: 8_000,
}

# ==============================================================================
# 3. COEFFICIENTS HÉDONIQUES (RELATIFS & ADDITIFS)
# ==============================================================================

# Vue
PRIME_VUE_MER = {
    "AUCUNE": 0.00,
    "APERÇU": 0.05,
    "BELLE_VUE": 0.12,
    "EXCEPTIONNELLE_FRONT_MER": 0.22,
}

# Étage (Appartement)
COEFF_ETAGE = {
    "RDC_SANS_JARDIN": -0.06,
    "RDC_AVEC_JARDIN": +0.02,
    "INTERMEDIAIRE": 0.00,
    "ETAGE_ELEVE": +0.04,
    "DERNIER_ETAGE_ATTIQUE": +0.10,
}

# État général
COEFF_ETAT = {
    "A_RENOVER_LOURD": -0.25,
    "TRAVAUX_RAFRAICHISSEMENT": -0.10,
    "BON_ETAT": 0.00,
    "RENOVE_HAUT_STANDING": +0.12,
}

# Extérieurs & Dépendances (Valeurs additives en F CFP)
VALEUR_PISCINE = {
    "AUCUNE": 0,
    "HORS_SOL_SEMI_ENTERREE": 1_500_000,
    "COQUE_POLYESTER": 2_800_000,
    "MACONNEE_LAGON": 4_800_000,
}

VALEUR_STATIONNEMENT = {
    "AUCUN": 0,
    "PARKING_EXT_SECURISE": 800_000,
    "CARPORT_COUVERT": 1_300_000,
    "GARAGE_FERME_BOX": 2_400_000,
}

# Varangue / Terrasse couverte : valorisée à 35% de la valeur au m² habitable
RATIO_SURFACE_VARANGUE = 0.35

# Deck extérieur en bois (kohu / pin traité) : valeur forfaitaire au m²
VALEUR_M2_DECK_BOIS = 22_000  # F CFP / m²

# Climatisation intégrale
VALEUR_CLIM_INTEGRALE = 700_000  # F CFP

# ==============================================================================
# 4. COEFFICIENT DE CONJONCTURE & LIQUIDITÉ TERRITORIALE (POST-MAI 2024)
# Prend en compte la prime d'illiquidité et la facilité de transaction locale.
# ==============================================================================
FACTEUR_LIQUIDITE_SECTEUR = {
    "NOUMEA_SUD": 0.98,        # Anse Vata, BDC, Val Plaisance, Ouémo, Tuband
    "NOUMEA_RESIDENTIEL": 0.93, # VDC, Faubourg Blanchot, Magenta, Port Plaisance
    "NOUMEA_NORD": 0.88,       # Vallée du Tir, Rivière Salée, Ducos
    "DUMBEA_SUD": 0.86,        # Koutio, Auteuil
    "DUMBEA_MER": 0.88,        # Dumbéa-sur-Mer
    "PAITA_RESIDENTIEL": 0.90, # Savannah, Beauvallon
    "PAITA_AUTRE": 0.84,       # Village, Gadji, Mont-Mou
    "MONT_DORE_NORD": 0.85,    # Pont des Français, Robinson, Boulari
    "MONT_DORE_SUD": 0.78,     # Vallon-Dore, La Coulée, Plum (enclavement circulation)
}

# ==============================================================================
# 5. RENDEMENTS LOCATIFS BRUTS DE RÉFÉRENCE (POUR ESTIMATION LOCATIVE)
# ==============================================================================
RENDEMENT_LOCATIF_BRUT_SECTEUR = {
    "NOUMEA_SUD": 0.052,        # 5.2% (valeur patrimoniale élevée, rendement modéré)
    "NOUMEA_RESIDENTIEL": 0.058, # 5.8%
    "NOUMEA_NORD": 0.068,       # 6.8%
    "DUMBEA_MER": 0.063,        # 6.3%
    "DUMBEA_SUD": 0.066,        # 6.6% (locatif populaire / intermédiaire)
    "PAITA_RESIDENTIEL": 0.060, # 6.0%
    "PAITA_AUTRE": 0.064,       # 6.4%
    "MONT_DORE_NORD": 0.062,    # 6.2%
    "MONT_DORE_SUD": 0.060,     # 6.0%
}
