"""
Moteur d'Évaluation Immobilière Automatisée (AVM) pour le Grand Nouméa.
Modélisation hédonique transparente et explicable adaptée au contexte calédonien.
"""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from src.config.settings import XPF_TO_EUR_RATE
from src.models.listing import Commune, PropertyType
from src.reference.geo import GeoReferential
from src.valuation.constants import (
    PRIX_BASE_M2_QUARTIER,
    PRIX_DEFAUT_COMMUNE,
    PRIX_M2_TERRAIN_PAR_COMMUNE,
    PRIME_VUE_MER,
    COEFF_ETAGE,
    COEFF_ETAT,
    VALEUR_PISCINE,
    VALEUR_STATIONNEMENT,
    RATIO_SURFACE_VARANGUE,
    VALEUR_M2_DECK_BOIS,
    VALEUR_CLIM_INTEGRALE,
    FACTEUR_LIQUIDITE_SECTEUR,
    RENDEMENT_LOCATIF_BRUT_SECTEUR,
)


class PropertyValuationRequest(BaseModel):
    commune: Commune
    quartier: Optional[str] = None
    property_type: PropertyType = PropertyType.APPARTEMENT
    surface_habitable_m2: float = Field(gt=0, description="Surface habitable intérieure en m²")
    surface_varangue_m2: float = Field(default=0.0, ge=0, description="Terrasse couverte / varangue")
    surface_deck_m2: float = Field(default=0.0, ge=0, description="Deck extérieur non couvert")
    surface_terrain_m2: float = Field(default=0.0, ge=0, description="Surface totale du terrain (pour villa)")
    rooms: Optional[int] = Field(default=None, ge=1, description="Nombre de pièces (F1, F2...)")
    vue_mer: str = Field(default="AUCUNE", description="AUCUNE, APERÇU, BELLE_VUE, EXCEPTIONNELLE_FRONT_MER")
    etage: str = Field(default="INTERMEDIAIRE", description="RDC_SANS_JARDIN, RDC_AVEC_JARDIN, INTERMEDIAIRE, ETAGE_ELEVE, DERNIER_ETAGE_ATTIQUE")
    etat_bien: str = Field(default="BON_ETAT", description="A_RENOVER_LOURD, TRAVAUX_RAFRAICHISSEMENT, BON_ETAT, RENOVE_HAUT_STANDING")
    piscine: str = Field(default="AUCUNE", description="AUCUNE, HORS_SOL_SEMI_ENTERREE, COQUE_POLYESTER, MACONNEE_LAGON")
    parking_type: str = Field(default="AUCUN", description="AUCUN, PARKING_EXT_SECURISE, CARPORT_COUVERT, GARAGE_FERME_BOX")
    nb_parkings: int = Field(default=1, ge=0)
    has_air_conditioning: bool = Field(default=True, description="Climatisation intégrale")
    is_secured: bool = Field(default=False, description="Résidence sécurisée avec digicode/volets")


class HedonicAdjustment(BaseModel):
    label: str
    category: str
    impact_xpf: int
    impact_pct: Optional[float] = None
    description: str


class ValuationResult(BaseModel):
    request: PropertyValuationRequest
    valeur_centrale_xpf: int
    valeur_centrale_eur: float
    fourchette_basse_xpf: int
    fourchette_haute_xpf: int
    fourchette_basse_eur: float
    fourchette_haute_eur: float
    prix_m2_moyen_xpf: int
    prix_m2_moyen_eur: float
    loyer_mensuel_estime_xpf: int
    loyer_mensuel_estime_eur: float
    rendement_locatif_brut_pct: float
    ajustements: List[HedonicAdjustment]
    facteur_conjoncture: float
    indice_confiance: str


class HedonicValuationEngine:
    def __init__(self, geo_ref: Optional[GeoReferential] = None):
        self.geo_ref = geo_ref or GeoReferential()

    def _get_base_price_m2(self, commune: Commune, quartier: Optional[str], prop_type: PropertyType) -> int:
        """Récupère le prix au m² de base pour le quartier et type de bien."""
        is_appt = (prop_type == PropertyType.APPARTEMENT)

        if quartier and commune in PRIX_BASE_M2_QUARTIER:
            commune_dict = PRIX_BASE_M2_QUARTIER[commune]
            # Recherche insensible à la casse
            for q_name, (p_appt, p_villa) in commune_dict.items():
                if q_name.lower() == quartier.lower():
                    return p_appt if is_appt else p_villa

        # Valeur de secours par commune
        default_p_appt, default_p_villa = PRIX_DEFAUT_COMMUNE.get(commune, (300_000, 280_000))
        return default_p_appt if is_appt else default_p_villa

    def _get_sector_key(self, commune: Commune, quartier: Optional[str]) -> str:
        """Détermine la clé de secteur pour les facteurs de conjoncture et rendements."""
        q_lower = (quartier or "").lower()

        if commune == Commune.NOUMEA:
            if any(k in q_lower for k in ["anse vata", "citrons", "val plaisance", "ouemo", "ouémo", "n'gea", "tuband"]):
                return "NOUMEA_SUD"
            if any(k in q_lower for k in ["tir", "salee", "salée", "ducos"]):
                return "NOUMEA_NORD"
            return "NOUMEA_RESIDENTIEL"

        if commune == Commune.DUMBEA:
            if "mer" in q_lower:
                return "DUMBEA_MER"
            return "DUMBEA_SUD"

        if commune == Commune.PAITA:
            if any(k in q_lower for k in ["savannah", "beauvallon", "val boise", "val boisé"]):
                return "PAITA_RESIDENTIEL"
            return "PAITA_AUTRE"

        if commune == Commune.MONT_DORE:
            if any(k in q_lower for k in ["vallon", "coulee", "coulée", "plum"]):
                return "MONT_DORE_SUD"
            return "MONT_DORE_NORD"

        return "NOUMEA_RESIDENTIEL"

    def evaluate(self, req: PropertyValuationRequest) -> ValuationResult:
        """Exécute l'évaluation complète d'un bien."""
        adjustments: List[HedonicAdjustment] = []

        # 1. Base Habitable
        prix_base_m2 = self._get_base_price_m2(req.commune, req.quartier, req.property_type)
        valeur_base = int(req.surface_habitable_m2 * prix_base_m2)
        adjustments.append(HedonicAdjustment(
            label="Base habitable",
            category="BASE",
            impact_xpf=valeur_base,
            impact_pct=None,
            description=f"{req.surface_habitable_m2:.1f} m² hab. @ {prix_base_m2:,} F/m² (Secteur {req.quartier or req.commune.value})".replace(",", " ")
        ))

        # 2. Coefficients relatifs sur la base habitable (Vue, Étage, État)
        cumul_pct = 0.0

        # Prime vue mer
        pct_vue = PRIME_VUE_MER.get(req.vue_mer, 0.0)
        if pct_vue > 0:
            cumul_pct += pct_vue
            impact_vue = int(valeur_base * pct_vue)
            adjustments.append(HedonicAdjustment(
                label=f"Prime vue mer ({req.vue_mer})",
                category="VUE",
                impact_xpf=impact_vue,
                impact_pct=pct_vue * 100,
                description=f"+{pct_vue*100:.0f}% sur la valeur habitable"
            ))

        # Étage (pour appartements)
        if req.property_type == PropertyType.APPARTEMENT:
            pct_etage = COEFF_ETAGE.get(req.etage, 0.0)
            if pct_etage != 0.0:
                cumul_pct += pct_etage
                impact_etage = int(valeur_base * pct_etage)
                adjustments.append(HedonicAdjustment(
                    label=f"Position / Étage ({req.etage})",
                    category="ETAGE",
                    impact_xpf=impact_etage,
                    impact_pct=pct_etage * 100,
                    description=f"{'+' if pct_etage > 0 else ''}{pct_etage*100:.0f}%"
                ))

        # État général
        pct_etat = COEFF_ETAT.get(req.etat_bien, 0.0)
        if pct_etat != 0.0:
            cumul_pct += pct_etat
            impact_etat = int(valeur_base * pct_etat)
            adjustments.append(HedonicAdjustment(
                label=f"État général ({req.etat_bien})",
                category="ETAT",
                impact_xpf=impact_etat,
                impact_pct=pct_etat * 100,
                description=f"{'+' if pct_etat > 0 else ''}{pct_etat*100:.0f}% sur valeur intrinsèque"
            ))

        # Sous-total base pondérée
        sous_total_bati = int(valeur_base * (1.0 + cumul_pct))

        # 3. Valorisations forfaitaires additives (Extérieurs, Varangue, Piscine, Parkings)
        valeur_additifs = 0

        # Varangue / Terrasse couverte
        if req.surface_varangue_m2 > 0:
            prix_m2_varangue = int(prix_base_m2 * RATIO_SURFACE_VARANGUE)
            val_varangue = int(req.surface_varangue_m2 * prix_m2_varangue)
            valeur_additifs += val_varangue
            adjustments.append(HedonicAdjustment(
                label="Varangue / Terrasse couverte",
                category="EXTERIEURS",
                impact_xpf=val_varangue,
                impact_pct=None,
                description=f"{req.surface_varangue_m2:.1f} m² @ {prix_m2_varangue:,} F/m² (ratio 35%)".replace(",", " ")
            ))

        # Deck extérieur bois
        if req.surface_deck_m2 > 0:
            val_deck = int(req.surface_deck_m2 * VALEUR_M2_DECK_BOIS)
            valeur_additifs += val_deck
            adjustments.append(HedonicAdjustment(
                label="Deck extérieur bois",
                category="EXTERIEURS",
                impact_xpf=val_deck,
                impact_pct=None,
                description=f"{req.surface_deck_m2:.1f} m² @ {VALEUR_M2_DECK_BOIS:,} F/m²".replace(",", " ")
            ))

        # Piscine
        val_piscine = VALEUR_PISCINE.get(req.piscine, 0)
        if val_piscine > 0:
            valeur_additifs += val_piscine
            adjustments.append(HedonicAdjustment(
                label=f"Piscine ({req.piscine})",
                category="EXTERIEURS",
                impact_xpf=val_piscine,
                impact_pct=None,
                description=f"Apport valeur vénale : {val_piscine:,} F CFP".replace(",", " ")
            ))

        # Stationnement
        val_unit_parking = VALEUR_STATIONNEMENT.get(req.parking_type, 0)
        if val_unit_parking > 0 and req.nb_parkings > 0:
            total_parking = val_unit_parking * req.nb_parkings
            valeur_additifs += total_parking
            adjustments.append(HedonicAdjustment(
                label=f"Stationnement ({req.nb_parkings}x {req.parking_type})",
                category="DEPENDANCES",
                impact_xpf=total_parking,
                impact_pct=None,
                description=f"{req.nb_parkings} place(s) @ {val_unit_parking:,} F".replace(",", " ")
            ))

        # Terrain résiduel (pour les villas)
        if req.property_type == PropertyType.MAISON_VILLA and req.surface_terrain_m2 > 0:
            # Emprise au sol approximative soustraite (habitable / 1.2)
            emprise = req.surface_habitable_m2
            terrain_utile = max(0.0, req.surface_terrain_m2 - emprise)
            if terrain_utile > 0:
                prix_m2_foncier = PRIX_M2_TERRAIN_PAR_COMMUNE.get(req.commune, 12_000)
                val_terrain = int(terrain_utile * prix_m2_foncier)
                valeur_additifs += val_terrain
                adjustments.append(HedonicAdjustment(
                    label="Foncier résiduel",
                    category="FONCIER",
                    impact_xpf=val_terrain,
                    impact_pct=None,
                    description=f"{terrain_utile:.0f} m² utile ({terrain_utile/100:.1f} ares) @ {prix_m2_foncier:,} F/m²".replace(",", " ")
                ))

        # Climatisation intégrale
        if req.has_air_conditioning:
            valeur_additifs += VALEUR_CLIM_INTEGRALE
            adjustments.append(HedonicAdjustment(
                label="Climatisation intégrale",
                category="CONFORT",
                impact_xpf=VALEUR_CLIM_INTEGRALE,
                impact_pct=None,
                description="Climatiseurs split récents toutes pièces"
            ))

        # 4. Facteur de conjoncture / liquidité post-2024
        sector_key = self._get_sector_key(req.commune, req.quartier)
        facteur_liquidite = FACTEUR_LIQUIDITE_SECTEUR.get(sector_key, 0.90)

        valeur_brute = sous_total_bati + valeur_additifs
        valeur_centrale = int(valeur_brute * facteur_liquidite)

        if facteur_liquidite != 1.0:
            impact_liq = valeur_centrale - valeur_brute
            adjustments.append(HedonicAdjustment(
                label="Ajustement liquidité & conjoncture",
                category="CONJONCTURE",
                impact_xpf=impact_liq,
                impact_pct=(facteur_liquidite - 1.0) * 100,
                description=f"Facteur {facteur_liquidite:.2f} (Secteur {sector_key})"
            ))

        # 5. Fourchettes de négociation (-7% vente rapide / +7% marché porteur)
        fourchette_basse = int(valeur_centrale * 0.93)
        fourchette_haute = int(valeur_centrale * 1.07)

        # 6. Estimation locative & Rendement
        rendement_cible = RENDEMENT_LOCATIF_BRUT_SECTEUR.get(
            sector_key if sector_key in RENDEMENT_LOCATIF_BRUT_SECTEUR else "NOUMEA_RESIDENTIEL",
            0.06
        )
        loyer_mensuel = int((valeur_centrale * rendement_cible) / 12)

        indice_confiance = "ÉLEVÉ" if req.quartier in PRIX_BASE_M2_QUARTIER.get(req.commune, {}) else "MOYEN"

        return ValuationResult(
            request=req,
            valeur_centrale_xpf=valeur_centrale,
            valeur_centrale_eur=round(valeur_centrale / XPF_TO_EUR_RATE, 2),
            fourchette_basse_xpf=fourchette_basse,
            fourchette_haute_xpf=fourchette_haute,
            fourchette_basse_eur=round(fourchette_basse / XPF_TO_EUR_RATE, 2),
            fourchette_haute_eur=round(fourchette_haute / XPF_TO_EUR_RATE, 2),
            prix_m2_moyen_xpf=int(valeur_centrale / req.surface_habitable_m2),
            prix_m2_moyen_eur=round((valeur_centrale / req.surface_habitable_m2) / XPF_TO_EUR_RATE, 2),
            loyer_mensuel_estime_xpf=loyer_mensuel,
            loyer_mensuel_estime_eur=round(loyer_mensuel / XPF_TO_EUR_RATE, 2),
            rendement_locatif_brut_pct=round(rendement_cible * 100, 2),
            ajustements=adjustments,
            facteur_conjoncture=facteur_liquidite,
            indice_confiance=indice_confiance,
        )
