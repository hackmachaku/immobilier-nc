import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.storage.database import PropertyDatabase
from src.utils.logger import DEFAULT_LOG_FILE, LOGS_DIR, get_logger

logger = get_logger("audit")


class PipelineAuditor:
    """Analyse les fichiers de logs et valide l'intégrité des données renvoyées par les scripts."""

    def __init__(self, log_path: Path = DEFAULT_LOG_FILE, db: PropertyDatabase = None):
        self.log_path = log_path
        self.db = db or PropertyDatabase()
        self.console = Console()

    def analyze_logs(self) -> Dict[str, Any]:
        """Analyse le fichier de log pour identifier le statut, le nombre d'erreurs et d'avertissements."""
        if not self.log_path.exists():
            return {
                "file_exists": False,
                "total_lines": 0,
                "info_count": 0,
                "warning_count": 0,
                "error_count": 0,
                "errors": [],
                "warnings": [],
            }

        total_lines = 0
        info_count = 0
        warning_count = 0
        error_count = 0
        critical_count = 0
        errors: List[str] = []
        warnings: List[str] = []

        with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                total_lines += 1
                if " | ERROR    | " in line or "ERROR:" in line:
                    error_count += 1
                    errors.append(f"L{line_no}: {line.strip()}")
                elif " | WARNING  | " in line or "WARNING:" in line:
                    warning_count += 1
                    warnings.append(f"L{line_no}: {line.strip()}")
                elif " | CRITICAL | " in line:
                    critical_count += 1
                    errors.append(f"L{line_no} [CRITICAL]: {line.strip()}")
                elif " | INFO     | " in line:
                    info_count += 1

        return {
            "file_exists": True,
            "log_path": str(self.log_path),
            "total_lines": total_lines,
            "info_count": info_count,
            "warning_count": warning_count,
            "error_count": error_count + critical_count,
            "errors": errors[-10:],  # 10 dernières erreurs maximum
            "warnings": warnings[-10:],
        }

    def audit_database_data(self) -> Dict[str, Any]:
        """Contrôle la cohérence, l'exhaustivité et la non-régression des données DuckDB."""
        with self.db.get_connection() as con:
            # 1. Total annonces
            total = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
            actives = con.execute("SELECT COUNT(*) FROM listings WHERE is_active = TRUE").fetchone()[0]

            # 2. Contrôle de validité des champs obligatoires
            null_prices = con.execute("SELECT COUNT(*) FROM listings WHERE price_xpf IS NULL OR price_xpf <= 0").fetchone()[0]
            null_surfaces = con.execute("""
                SELECT COUNT(*) FROM listings 
                WHERE (property_type IN ('APPARTEMENT', 'MAISON_VILLA', 'DOCK', 'LOCAL_COMMERCIAL')
                       AND (surface_habitable_m2 IS NULL OR surface_habitable_m2 <= 0))
                   OR (property_type = 'TERRAIN'
                       AND (surface_terrain_m2 IS NULL OR surface_terrain_m2 <= 0))
            """).fetchone()[0]
            calculated_prix_m2 = con.execute("SELECT COUNT(*) FROM listings WHERE prix_m2_habitable_xpf IS NOT NULL").fetchone()[0]

            # 3. Répartition par source de données
            sources_breakdown = con.execute("""
                SELECT source, COUNT(*) as count, ROUND(AVG(price_xpf), 0) as avg_price, ROUND(AVG(prix_m2_habitable_xpf), 0) as avg_m2
                FROM listings
                GROUP BY source
                ORDER BY count DESC
            """).df().to_dict(orient="records")

            # 4. Répartition par commune
            communes_breakdown = con.execute("""
                SELECT commune, COUNT(*) as count
                FROM listings
                GROUP BY commune
                ORDER BY count DESC
            """).df().to_dict(orient="records")

            # 5. Vérification des vues analytiques
            view_quartier_count = con.execute("SELECT COUNT(*) FROM v_marche_par_quartier").fetchone()[0]
            view_typologie_count = con.execute("SELECT COUNT(*) FROM v_marche_par_typologie").fetchone()[0]

        is_valid = (
            total > 0
            and null_prices == 0
            and (null_surfaces / total <= 0.35 if total > 0 else True)  # Tolérance réaliste sur annonces web hétérogènes (≥65% conformes)
            and view_quartier_count > 0
        )

        return {
            "total_listings": total,
            "active_listings": actives,
            "data_quality": {
                "null_prices": null_prices,
                "null_surfaces": null_surfaces,
                "valid_m2_ratio_pct": round(((total - null_surfaces) / total) * 100.0, 1) if total > 0 else 100.0,
                "is_clean": (null_prices == 0 and null_surfaces == 0),
            },
            "sources_breakdown": sources_breakdown,
            "communes_breakdown": communes_breakdown,
            "views_functional": {
                "v_marche_par_quartier_rows": view_quartier_count,
                "v_marche_par_typologie_rows": view_typologie_count,
            },
            "is_valid": is_valid,
        }

    def run_full_audit(self) -> Dict[str, Any]:
        """Exécute l'audit complet (Logs + Données) et enregistre le rapport JSON."""
        log_report = self.analyze_logs()
        db_report = self.audit_database_data()

        is_healthy = log_report["error_count"] == 0 and db_report["is_valid"]
        status = "HEALTHY" if is_healthy else "WARNING_OR_ERROR"

        audit_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "is_healthy": is_healthy,
            "logs_summary": log_report,
            "database_summary": db_report,
        }

        # Sauvegarde du rapport JSON
        report_file = LOGS_DIR / "audit_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(audit_result, f, indent=2, ensure_ascii=False)

        return audit_result

    def print_audit_report(self, audit_result: Dict[str, Any]):
        """Affiche un tableau récapitulatif d'audit dans la console."""
        logs = audit_result["logs_summary"]
        db = audit_result["database_summary"]
        is_healthy = audit_result["is_healthy"]

        status_color = "bold green" if is_healthy else "bold red"
        status_text = "VALIDE & OPERATIONNEL (0 ERREUR)" if is_healthy else "ANOMALIE DETECTEE"

        self.console.print()
        self.console.print(Panel(
            f"Statut Global : [{status_color}]{status_text}[/{status_color}]\n"
            f"Fichier de logs : [cyan]{logs.get('log_path', 'N/A')}[/cyan]\n"
            f"Lignes analysées : [bold]{logs['total_lines']}[/bold] | "
            f"Infos : [green]{logs['info_count']}[/green] | "
            f"Warnings : [yellow]{logs['warning_count']}[/yellow] | "
            f"Erreurs : [red]{logs['error_count']}[/red]",
            title="[bold cyan]RAPPORT D'AUDIT & ANALYSE D'EXECUTION DU PIPELINE[/bold cyan]",
            border_style="green" if is_healthy else "red"
        ))

        # Tableau des sources
        t_src = Table(title="Contrôle des Données par Source Active (DuckDB)")
        t_src.add_column("Plateforme Source", style="cyan")
        t_src.add_column("Biens Ingestionnés", justify="right", style="bold white")
        t_src.add_column("Prix Moyen (XPF)", justify="right")
        t_src.add_column("Prix/m² Moyen", justify="right", style="bold green")

        for s in db.get("sources_breakdown", []):
            t_src.add_row(
                str(s["source"]),
                str(s["count"]),
                f"{int(s['avg_price']):,} F".replace(",", " ") if s["avg_price"] else "-",
                f"{int(s['avg_m2']):,} F/m²".replace(",", " ") if s["avg_m2"] else "-",
            )
        self.console.print(t_src)

        # Qualité des données
        dq = db.get("data_quality", {})
        self.console.print(
            f"[bold]Qualité des données :[/bold] "
            f"Prix nuls = [bold green]{dq.get('null_prices', 0)}[/bold green] | "
            f"Surfaces nulles = [bold green]{dq.get('null_surfaces', 0)}[/bold green] | "
            f"Ratio m² calculé = [bold green]{dq.get('valid_m2_ratio_pct', 0)}%[/bold green] | "
            f"Total annonces actives = [bold green]{db.get('active_listings', 0)}[/bold green]\n"
        )
