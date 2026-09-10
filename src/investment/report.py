"""
Module de restitution du rapport d'investissement locatif et de cash-flow (Console & Tables).
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.investment.models import InvestmentResult


class InvestmentReporter:
    def __init__(self):
        self.console = Console()

    def print_investment_report(self, res: InvestmentResult):
        req = res.request

        header_title = f"SIMULATION FINANCIERE D'INVESTISSEMENT LOCATIF - {req.nom_projet}"
        self.console.print(f"\n[bold green]{'='*75}[/bold green]")
        self.console.print(f"[bold white]{header_title.center(75)}[/bold white]")
        self.console.print(f"[bold green]{'='*75}[/bold green]\n")

        # 1. Structure du projet et financement
        t_fin = Table(title="1. Structure du Financement & Coûts d'Acquisition")
        t_fin.add_column("Poste", style="cyan", justify="left")
        t_fin.add_column("Montant (F CFP)", justify="right", style="bold")
        t_fin.add_column("Contre-valeur (€)", justify="right")
        t_fin.add_column("Commentaire / Taux", style="dim", justify="left")

        t_fin.add_row("Prix d'acquisition net / FAI", f"{req.prix_acquisition_xpf:,} F", f"{req.prix_acquisition_xpf/119.3317:,.0f} €", "Base négociée")
        t_fin.add_row("Frais de notaire & mutation (NC)", f"{res.frais_notaire_xpf:,} F", f"{res.frais_notaire_xpf/119.3317:,.0f} €", f"{req.frais_notaire_taux*100:.1f}% (barème territorial)")
        if req.montant_travaux_xpf > 0:
            t_fin.add_row("Enveloppe travaux & aménagement", f"{req.montant_travaux_xpf:,} F", f"{req.montant_travaux_xpf/119.3317:,.0f} €", "Prévus")
        t_fin.add_row("Frais de dossier / garantie", f"{req.frais_bancaires_xpf:,} F", f"{req.frais_bancaires_xpf/119.3317:,.0f} €", "Frais bancaires")
        t_fin.add_row("[bold]COÛT TOTAL DU PROJET[/bold]", f"[bold]{res.cout_total_projet_xpf:,} F[/bold]", f"[bold]{res.cout_total_projet_eur:,.0f} €[/bold]", "[bold]Total investissement[/bold]")
        t_fin.add_row("Apport personnel injecté", f"{res.apport_personnel_xpf:,} F", f"{res.apport_personnel_xpf/119.3317:,.0f} €", "Fonds propres")
        t_fin.add_row("[yellow]Montant du crédit bancaire[/yellow]", f"[yellow]{res.montant_emprunte_xpf:,} F[/yellow]", f"{res.montant_emprunte_xpf/119.3317:,.0f} €", f"{req.taux_emprunt_annuel_pct}% sur {req.duree_emprunt_annees} ans")
        t_fin.add_row("[bold yellow]Mensualité de crédit[/bold yellow]", f"[bold yellow]{res.mensualite_credit_xpf:,} F / mois[/bold yellow]", f"{res.mensualite_credit_xpf/119.3317:,.0f} €/mois", "Amortissement constant")

        self.console.print(t_fin)

        # 2. Bilan d'exploitation annuel
        t_exp = Table(title="2. Bilan d'Exploitation Annuel & Charges Récurrentes")
        t_exp.add_column("Poste d'Exploitation", style="cyan", justify="left")
        t_exp.add_column("Annuel (F CFP)", justify="right", style="bold")
        t_exp.add_column("Mensuel Équivalent", justify="right")
        t_exp.add_column("Hypothèse retenue", style="dim", justify="left")

        t_exp.add_row("Loyer brut théorique", f"+{res.loyer_annuel_brut_theorique_xpf:,} F", f"+{req.loyer_mensuel_xpf:,} F/mois", "12 mois pleins")
        t_exp.add_row("Provision vacance locative", f"-{res.perte_vacance_annuelle_xpf:,} F", f"-{int(res.perte_vacance_annuelle_xpf/12):,} F/mois", f"{req.taux_vacance_locative_pct}% de vacance")
        t_exp.add_row("[green]Loyer effectif encaissé[/green]", f"[green]+{res.loyer_annuel_encaisse_xpf:,} F[/green]", f"[green]+{int(res.loyer_annuel_encaisse_xpf/12):,} F/mois[/green]", "Base nette de vacance")
        t_exp.add_row("Charges copropriété non récup.", f"-{req.charges_copro_mensuelles_non_recup_xpf*12:,} F", f"-{req.charges_copro_mensuelles_non_recup_xpf:,} F/mois", "Quote-part bailleur")
        t_exp.add_row("Contribution foncière (Taxe foncière)", f"-{req.taxe_fonciere_annuelle_xpf:,} F", f"-{int(req.taxe_fonciere_annuelle_xpf/12):,} F/mois", "Commune NC")
        t_exp.add_row("Assurance PNO", f"-{req.assurance_pno_annuelle_xpf:,} F", f"-{int(req.assurance_pno_annuelle_xpf/12):,} F/mois", "Propriétaire Non-Occupant")
        t_exp.add_row("Gestion locative agence + TGC", f"-{int(res.loyer_annuel_encaisse_xpf*(req.frais_gestion_agence_pct/100)*(1.11)):,} F", f"-{int((res.loyer_annuel_encaisse_xpf*(req.frais_gestion_agence_pct/100)*(1.11))/12):,} F/mois", f"{req.frais_gestion_agence_pct}% + TGC 11%")
        t_exp.add_row("Provision entretien / travaux", f"-{req.provision_travaux_annuelle_xpf:,} F", f"-{int(req.provision_travaux_annuelle_xpf/12):,} F/mois", "Réserve clim / maintenance")
        t_exp.add_row("[bold red]TOTAL CHARGES ANNUELLES[/bold red]", f"[bold red]-{res.total_charges_annuelles_xpf:,} F[/bold red]", f"[bold red]-{int(res.total_charges_annuelles_xpf/12):,} F/mois[/bold red]", "Total décaissé hors crédit")
        t_exp.add_row("[bold green]REVENU NET D'EXPLOITATION (NOI)[/bold green]", f"[bold green]+{res.revenu_net_annuel_avant_credit_xpf:,} F[/bold green]", f"[bold green]+{int(res.revenu_net_annuel_avant_credit_xpf/12):,} F/mois[/bold green]", "Avant service de la dette")

        self.console.print(t_exp)

        # 3. Synthèse des rendements & Cash-Flow
        cf_color = "green" if res.cash_flow_mensuel_net_xpf >= 0 else "red"
        cf_label = "EXCÉDENT DE TRÉSORERIE" if res.cash_flow_mensuel_net_xpf >= 0 else "EFFORT D'ÉPARGNE MENSUEL"

        perf_summary = (
            f"[bold]INDICATEURS DE PERFORMANCE :[/bold]\n"
            f"  • [bold]Rendement Locatif Brut :[/bold] [yellow]{res.rendement_locatif_brut_pct:.2f} %[/yellow] (Loyer brut / Prix d'achat)\n"
            f"  • [bold]Rendement Net de Charges :[/bold] [green]{res.rendement_locatif_net_charges_pct:.2f} %[/green] (NOI / Coût total projet)\n"
            f"  • [bold]Taux de Rendement Interne (TRI 10 ans) :[/bold] [bold cyan]{res.tri_10_ans_pct:.2f} %[/bold cyan]\n"
            f"  • [bold]Taux de Rendement Interne (TRI 15 ans) :[/bold] [bold cyan]{res.tri_15_ans_pct:.2f} %[/bold cyan]\n\n"
            f"[{cf_color} bold]CASH-FLOW NET D'EXPLOITATION :[/{cf_color} bold]\n"
            f"  • Cash-flow annuel net : [{cf_color} bold]{res.cash_flow_annuel_net_xpf:+,} F CFP / an[/{cf_color} bold]\n"
            f"  • {cf_label} : [{cf_color} bold]{res.cash_flow_mensuel_net_xpf:+,} F CFP / mois[/{cf_color} bold] ({res.cash_flow_mensuel_net_eur:+,.0f} €/mois)"
        ).replace(",", " ")

        self.console.print(Panel(perf_summary, title="3. Rentrabilité & Flux Nets de Trésorerie", border_style=cf_color))

        # 4. Tableau des Stress-Tests
        t_stress = Table(title="4. Analyse de Sensibilité & Stress-Tests")
        t_stress.add_column("Scénario Dégradé", style="yellow", justify="left")
        t_stress.add_column("Mensualité Crédit", justify="right")
        t_stress.add_column("Cash-Flow Net Mensuel", justify="right", style="bold")
        t_stress.add_column("Impact sur trésorerie", justify="right", style="red")

        for key, st in res.stress_tests.items():
            cf_st_color = "green" if st.cash_flow_mensuel_xpf >= 0 else "red"
            t_stress.add_row(
                st.nom,
                f"{st.mensualite_credit_xpf:,} F".replace(",", " "),
                f"[{cf_st_color}]{st.cash_flow_mensuel_xpf:+,} F[/{cf_st_color}]".replace(",", " "),
                f"{st.impact_mensuel_xpf:+,} F/mois".replace(",", " "),
            )

        self.console.print(t_stress)
