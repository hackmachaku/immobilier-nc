"""
Module de restitution et explicabilité du rapport d'expertise immobilière (AVM).
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.valuation.avm import ValuationResult


class ValuationExplainer:
    def __init__(self):
        self.console = Console()

    def print_console_report(self, res: ValuationResult):
        req = res.request

        # En-tête du rapport
        title = f"RAPPORT D'ESTIMATION IMMOBILIERE AVM - {req.commune.value} ({req.quartier or 'Centre'})"
        self.console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
        self.console.print(f"[bold white]{title.center(70)}[/bold white]")
        self.console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

        # Résumé du bien
        summary_text = (
            f"[bold]Type de bien :[/bold] {req.property_type.value}\n"
            f"[bold]Localisation :[/bold] {req.commune.value} - {req.quartier or 'Non spécifié'}\n"
            f"[bold]Surface Habitable :[/bold] {req.surface_habitable_m2:.1f} m²"
        )
        if req.surface_varangue_m2 > 0:
            summary_text += f" | [bold]Varangue :[/bold] {req.surface_varangue_m2:.1f} m²"
        if req.surface_terrain_m2 > 0:
            summary_text += f" | [bold]Terrain :[/bold] {req.surface_terrain_m2/100:.1f} ares ({req.surface_terrain_m2:.0f} m²)"

        summary_text += (
            f"\n[bold]Vue :[/bold] {req.vue_mer} | [bold]État :[/bold] {req.etat_bien} | [bold]Piscine :[/bold] {req.piscine}\n"
            f"[bold]Indice de confiance du modèle :[/bold] [green]{res.indice_confiance}[/green]"
        )

        self.console.print(Panel(summary_text, title="Caractéristiques du Bien", border_style="blue"))

        # Tableau des ajustements hédoniques
        table = Table(title="Décomposition des Composantes de Valeur (Méthode Hédonique)")
        table.add_column("Poste de Valorisation", style="cyan", justify="left")
        table.add_column("Catégorie", style="magenta", justify="center")
        table.add_column("Détail / Hypothèse", style="white", justify="left")
        table.add_column("Impact (F CFP)", justify="right", style="bold")
        table.add_column("Impact (%)", justify="right", style="yellow")

        for adj in res.ajustements:
            pct_str = f"{adj.impact_pct:+.1f}%" if adj.impact_pct is not None else "-"
            val_style = "green" if adj.impact_xpf >= 0 else "red"
            val_str = f"[{val_style}]{adj.impact_xpf:+,} F[/{val_style}]".replace(",", " ")
            table.add_row(adj.label, adj.category, adj.description, val_str, pct_str)

        self.console.print(table)

        # Synthèse financière
        fin_text = (
            f"[bold green]VALEUR VÉNALE ESTIMÉE : {res.valeur_centrale_xpf:,} F CFP[/bold green] "
            f"([bold white]{res.valeur_centrale_eur:,.0f} €[/bold white])\n"
            f"[dim]Prix moyen pondéré : {res.prix_m2_moyen_xpf:,} F CFP/m² ({res.prix_m2_moyen_eur:,.0f} €/m²)[/dim]\n\n"
            f"[bold yellow]Fourchette de négociation recommandée :[/bold yellow]\n"
            f"  - Fourchette basse (vente rapide / négociation tendue) : {res.fourchette_basse_xpf:,} F CFP ({res.fourchette_basse_eur:,.0f} €)\n"
            f"  - Fourchette haute (marché porteur / coup de cœur)      : {res.fourchette_haute_xpf:,} F CFP ({res.fourchette_haute_eur:,.0f} €)\n\n"
            f"[bold cyan]Potentiel Locatif & Rendement :[/bold cyan]\n"
            f"  - Loyer mensuel de marché estimé : [bold]{res.loyer_mensuel_estime_xpf:,} F CFP / mois[/bold] ({res.loyer_mensuel_estime_eur:,.0f} €/mois)\n"
            f"  - Rendement locatif brut prévisionnel : [bold green]{res.rendement_locatif_brut_pct:.2f} %[/bold green]"
        ).replace(",", " ")

        self.console.print(Panel(fin_text, title="Conclusion de l'Évaluation Vénale", border_style="green"))
