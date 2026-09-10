"""
Modèles Pydantic pour les simulations d'investissement locatif en Nouvelle-Calédonie.
Calcul des rendements bruts/nets, cash-flow mensuel et TRI en Francs Pacifique (XPF).
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, computed_field
from src.config.settings import XPF_TO_EUR_RATE


class InvestmentRequest(BaseModel):
    nom_projet: str = Field(default="Investissement Locatif Grand Nouméa")
    prix_acquisition_xpf: int = Field(gt=0, description="Prix d'achat du bien (F CFP)")
    frais_notaire_taux: float = Field(default=0.08, ge=0.0, le=0.15, description="Droits de mutation et frais de notaire en NC (~7.5% à 8.5%)")
    montant_travaux_xpf: int = Field(default=0, ge=0, description="Budget travaux d'aménagement ou rafraîchissement")
    frais_bancaires_xpf: int = Field(default=150_000, ge=0, description="Frais de dossier et garantie bancaire")

    # Financement
    apport_personnel_xpf: int = Field(default=0, ge=0, description="Apport personnel de l'investisseur")
    taux_emprunt_annuel_pct: float = Field(default=4.2, ge=0.5, le=12.0, description="Taux d'intérêt annuel du crédit (%)")
    duree_emprunt_annees: int = Field(default=20, ge=5, le=30, description="Durée de l'emprunt en années")

    # Revenus & Charges récurrentes en NC
    loyer_mensuel_xpf: int = Field(gt=0, description="Loyer mensuel prévu hors charges (F CFP)")
    taux_vacance_locative_pct: float = Field(default=5.0, ge=0.0, le=30.0, description="Taux de vacance locative estimé (%)")
    charges_copro_mensuelles_non_recup_xpf: int = Field(default=6_000, ge=0, description="Charges de copropriété à la charge du bailleur")
    taxe_fonciere_annuelle_xpf: int = Field(default=75_000, ge=0, description="Contribution foncière annuelle calédonienne")
    assurance_pno_annuelle_xpf: int = Field(default=40_000, ge=0, description="Assurance Propriétaire Non-Occupant annuelle")
    frais_gestion_agence_pct: float = Field(default=7.0, ge=0.0, le=15.0, description="Honoraires de gestion locative d'agence (%)")
    inclure_tgc_gestion: bool = Field(default=True, description="Appliquer la TGC calédonienne de 11% sur les honoraires de gestion")
    provision_travaux_annuelle_xpf: int = Field(default=50_000, ge=0, description="Réserve annuelle pour entretien et climatiseurs")

    # Hypothèses de sortie
    duree_detention_annees: int = Field(default=15, ge=5, le=25, description="Durée de projection pour le calcul du TRI")
    hypothese_revalorisation_annuelle_pct: float = Field(default=1.0, ge=-5.0, le=10.0, description="Évolution annuelle estimée de la valeur vénale (%)")


class StressTestScenario(BaseModel):
    nom: str
    mensualite_credit_xpf: int
    cash_flow_mensuel_xpf: int
    rendement_net_pct: float
    impact_mensuel_xpf: int


class InvestmentResult(BaseModel):
    request: InvestmentRequest

    # Coûts globaux d'acquisition
    frais_notaire_xpf: int
    cout_total_projet_xpf: int
    cout_total_projet_eur: float
    montant_emprunte_xpf: int
    apport_personnel_xpf: int

    # Crédit immobilier
    mensualite_credit_xpf: int
    cout_total_credit_xpf: int
    total_interets_xpf: int

    # Exploitation annuelle
    loyer_annuel_brut_theorique_xpf: int
    perte_vacance_annuelle_xpf: int
    loyer_annuel_encaisse_xpf: int
    total_charges_annuelles_xpf: int
    revenu_net_annuel_avant_credit_xpf: int

    # Rentrabilité & Cash-Flow
    cash_flow_annuel_net_xpf: int
    cash_flow_mensuel_net_xpf: int
    cash_flow_mensuel_net_eur: float
    rendement_locatif_brut_pct: float
    rendement_locatif_net_charges_pct: float
    rendement_locatif_net_net_pct: float
    tri_10_ans_pct: float
    tri_15_ans_pct: float

    # Scénarios de stress-test
    stress_tests: Dict[str, StressTestScenario]
