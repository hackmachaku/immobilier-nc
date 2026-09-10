"""
Moteur de calcul financier d'investissement immobilier pour la Nouvelle-Calédonie.
Calculs de crédit, amortissement, charges locales, cash-flow net, TRI et stress-tests.
"""

from typing import Dict, List, Tuple
import numpy as np

from src.config.settings import XPF_TO_EUR_RATE, TGC_IMMOBILIER_TAUX
from src.investment.models import InvestmentRequest, InvestmentResult, StressTestScenario


class InvestmentCalculator:
    """Calculateur financier calibré pour les investissements immobiliers en F CFP."""

    def calculate_mortgage(self, capital: int, taux_annuel_pct: float, duree_annees: int) -> Tuple[int, int, int]:
        """
        Calcule la mensualité constante, le coût total du crédit et le total des intérêts.
        Formule financière : M = C * [r * (1 + r)^n] / [(1 + r)^n - 1]
        """
        if capital <= 0:
            return 0, 0, 0

        r = (taux_annuel_pct / 100.0) / 12.0
        n = duree_annees * 12

        if r == 0:
            mensualite = int(capital / n)
            return mensualite, capital, 0

        mensualite = int(capital * (r * (1.0 + r)**n) / ((1.0 + r)**n - 1.0))
        cout_total = mensualite * n
        interets = cout_total - capital
        return mensualite, cout_total, interets

    def calculate_remaining_balance(self, capital: int, taux_annuel_pct: float, duree_annees: int, annee_cible: int) -> int:
        """Calcule le capital restant dû au terme d'un nombre d'années donné."""
        if capital <= 0 or annee_cible >= duree_annees:
            return 0

        r = (taux_annuel_pct / 100.0) / 12.0
        n = duree_annees * 12
        p = annee_cible * 12

        # Capital restant dû
        crd = capital * ((1.0 + r)**n - (1.0 + r)**p) / ((1.0 + r)**n - 1.0)
        return max(0, int(crd))

    def _calculate_irr(self, cash_flows: List[float]) -> float:
        """Calcule le Taux de Rendement Interne (TRI / IRR) d'une série de flux."""
        try:
            # Recherche de la racine du polynôme NPV(r) = 0
            roots = np.roots(cash_flows[::-1])
            # Ne garder que les racines réelles positives
            real_roots = [r.real for r in roots if np.isreal(r) and r.real > 0]
            if not real_roots:
                return 0.0
            # Le taux r tel que 1/(1+r) = root => r = (1/root) - 1
            rates = [(1.0 / root) - 1.0 for root in real_roots]
            # Filtrer les taux réalistes entre -50% et +100%
            valid_rates = [rate for rate in rates if -0.5 <= rate <= 1.0]
            if valid_rates:
                return round(float(valid_rates[0] * 100.0), 2)
            return 0.0
        except Exception:
            return 0.0

    def simulate(self, req: InvestmentRequest) -> InvestmentResult:
        """Exécute la simulation complète de l'investissement."""

        # 1. Coûts initiaux d'acquisition
        frais_notaire = int(req.prix_acquisition_xpf * req.frais_notaire_taux)
        cout_total_projet = req.prix_acquisition_xpf + frais_notaire + req.montant_travaux_xpf + req.frais_bancaires_xpf

        # Montant emprunté
        montant_emprunte = max(0, cout_total_projet - req.apport_personnel_xpf)

        # 2. Crédit immobilier
        mensualite, cout_credit, total_interets = self.calculate_mortgage(
            montant_emprunte, req.taux_emprunt_annuel_pct, req.duree_emprunt_annees
        )

        # 3. Exploitation annuelle
        loyer_brut_theorique = req.loyer_mensuel_xpf * 12
        perte_vacance = int(loyer_brut_theorique * (req.taux_vacance_locative_pct / 100.0))
        loyer_encaisse = loyer_brut_theorique - perte_vacance

        # Frais de gestion d'agence (avec TGC 11% locale si activée)
        taux_tgc = TGC_IMMOBILIER_TAUX if req.inclure_tgc_gestion else 0.0
        frais_gestion_annuels = int(loyer_encaisse * (req.frais_gestion_agence_pct / 100.0) * (1.0 + taux_tgc))

        total_charges_annuelles = (
            frais_gestion_annuels
            + (req.charges_copro_mensuelles_non_recup_xpf * 12)
            + req.taxe_fonciere_annuelle_xpf
            + req.assurance_pno_annuelle_xpf
            + req.provision_travaux_annuelle_xpf
        )

        revenu_net_avant_credit = loyer_encaisse - total_charges_annuelles

        # 4. Cash-Flow
        charge_credit_annuelle = mensualite * 12
        cash_flow_annuel = revenu_net_avant_credit - charge_credit_annuelle
        cash_flow_mensuel = int(cash_flow_annuel / 12)

        # 5. Rendements
        rendement_brut = round((loyer_brut_theorique / req.prix_acquisition_xpf) * 100.0, 2)
        rendement_net_charges = round((revenu_net_avant_credit / cout_total_projet) * 100.0, 2)
        rendement_net_net = round((cash_flow_annuel / cout_total_projet) * 100.0, 2)

        # 6. Calcul du TRI sur 10 et 15 ans
        def compute_tri_for_horizon(horizon_years: int) -> float:
            mise_initiale = req.apport_personnel_xpf if req.apport_personnel_xpf > 0 else cout_total_projet
            flows = [-float(mise_initiale)]

            crd = self.calculate_remaining_balance(
                montant_emprunte, req.taux_emprunt_annuel_pct, req.duree_emprunt_annees, horizon_years
            )
            # Revalorisation vénale du bien
            valeur_revente = int(req.prix_acquisition_xpf * (1.0 + (req.hypothese_revalorisation_annuelle_pct / 100.0))**horizon_years)
            net_vendeur_sortie = valeur_revente - crd

            for year in range(1, horizon_years):
                flows.append(float(cash_flow_annuel))

            # Dernière année : cash-flow + produit net de revente
            flows.append(float(cash_flow_annuel + net_vendeur_sortie))
            return self._calculate_irr(flows)

        tri_10 = compute_tri_for_horizon(10)
        tri_15 = compute_tri_for_horizon(15)

        # 7. Scénarios de Stress-Test
        stress_tests: Dict[str, StressTestScenario] = {}

        # Scénario A : Hausse des taux d'intérêt de +1.0%
        mens_st1, _, _ = self.calculate_mortgage(montant_emprunte, req.taux_emprunt_annuel_pct + 1.0, req.duree_emprunt_annees)
        cf_st1 = int((revenu_net_avant_credit - (mens_st1 * 12)) / 12)
        stress_tests["HAUSSE_TAUX_PLUS_1"] = StressTestScenario(
            nom="Hausse des taux de crédit (+1.0%)",
            mensualite_credit_xpf=mens_st1,
            cash_flow_mensuel_xpf=cf_st1,
            rendement_net_pct=rendement_net_charges,
            impact_mensuel_xpf=cf_st1 - cash_flow_mensuel,
        )

        # Scénario B : Vacance locative doublée (10%)
        perte_vac_st2 = int(loyer_brut_theorique * 0.10)
        loyer_enc_st2 = loyer_brut_theorique - perte_vac_st2
        frais_gest_st2 = int(loyer_enc_st2 * (req.frais_gestion_agence_pct / 100.0) * (1.0 + taux_tgc))
        tot_charges_st2 = (
            frais_gest_st2
            + (req.charges_copro_mensuelles_non_recup_xpf * 12)
            + req.taxe_fonciere_annuelle_xpf
            + req.assurance_pno_annuelle_xpf
            + req.provision_travaux_annuelle_xpf
        )
        cf_st2 = int(((loyer_enc_st2 - tot_charges_st2) - charge_credit_annuelle) / 12)
        stress_tests["VACANCE_DOUBLEE"] = StressTestScenario(
            nom="Vacance locative prolongée (10% soit ~5 sem/an)",
            mensualite_credit_xpf=mensualite,
            cash_flow_mensuel_xpf=cf_st2,
            rendement_net_pct=round(((loyer_enc_st2 - tot_charges_st2) / cout_total_projet) * 100.0, 2),
            impact_mensuel_xpf=cf_st2 - cash_flow_mensuel,
        )

        # Scénario C : Baisse de loyer de 10%
        loyer_mens_st3 = int(req.loyer_mensuel_xpf * 0.90)
        loyer_brut_st3 = loyer_mens_st3 * 12
        loyer_enc_st3 = loyer_brut_st3 - int(loyer_brut_st3 * (req.taux_vacance_locative_pct / 100.0))
        frais_gest_st3 = int(loyer_enc_st3 * (req.frais_gestion_agence_pct / 100.0) * (1.0 + taux_tgc))
        tot_charges_st3 = (
            frais_gest_st3
            + (req.charges_copro_mensuelles_non_recup_xpf * 12)
            + req.taxe_fonciere_annuelle_xpf
            + req.assurance_pno_annuelle_xpf
            + req.provision_travaux_annuelle_xpf
        )
        cf_st3 = int(((loyer_enc_st3 - tot_charges_st3) - charge_credit_annuelle) / 12)
        stress_tests["BAISSE_LOYER_10"] = StressTestScenario(
            nom="Baisse du loyer de marché (-10%)",
            mensualite_credit_xpf=mensualite,
            cash_flow_mensuel_xpf=cf_st3,
            rendement_net_pct=round(((loyer_enc_st3 - tot_charges_st3) / cout_total_projet) * 100.0, 2),
            impact_mensuel_xpf=cf_st3 - cash_flow_mensuel,
        )

        return InvestmentResult(
            request=req,
            frais_notaire_xpf=frais_notaire,
            cout_total_projet_xpf=cout_total_projet,
            cout_total_projet_eur=round(cout_total_projet / XPF_TO_EUR_RATE, 2),
            montant_emprunte_xpf=montant_emprunte,
            apport_personnel_xpf=req.apport_personnel_xpf,
            mensualite_credit_xpf=mensualite,
            cout_total_credit_xpf=cout_credit,
            total_interets_xpf=total_interets,
            loyer_annuel_brut_theorique_xpf=loyer_brut_theorique,
            perte_vacance_annuelle_xpf=perte_vacance,
            loyer_annuel_encaisse_xpf=loyer_encaisse,
            total_charges_annuelles_xpf=total_charges_annuelles,
            revenu_net_annuel_avant_credit_xpf=revenu_net_avant_credit,
            cash_flow_annuel_net_xpf=cash_flow_annuel,
            cash_flow_mensuel_net_xpf=cash_flow_mensuel,
            cash_flow_mensuel_net_eur=round(cash_flow_mensuel / XPF_TO_EUR_RATE, 2),
            rendement_locatif_brut_pct=rendement_brut,
            rendement_locatif_net_charges_pct=rendement_net_charges,
            rendement_locatif_net_net_pct=rendement_net_net,
            tri_10_ans_pct=tri_10,
            tri_15_ans_pct=tri_15,
            stress_tests=stress_tests,
        )
