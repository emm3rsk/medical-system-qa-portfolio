"""
Générateur de rendus pour le diagnostic :
1. Affichage console interactif avec Rich (Timeline colorée multi-sources).
2. Fiche de défaut au format Markdown prête à être copiée dans Target Process / ALM.
"""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from .models import DefectTicket, LogEntry, LogLevel, RCAFinding, Subsystem

console = Console()


def display_console_timeline(timeline: List[LogEntry], rca: Optional[RCAFinding], offset_ms: float):
    """Affiche la timeline unifiée et le panneau de diagnostic dans le terminal."""
    console.print("\n")
    console.print(
        Panel.fit(
            "[bold white]SYSTÈME D'IMAGERIE MÉDICALE - ANALYSEUR MULTI-LOGS DE DIAGNOSTIC[/bold white]\n"
            f"[dim]Horodatages réalignés • Décalage MCU appliqué : {offset_ms:+.1f} ms[/dim]",
            border_style="cyan",
        )
    )

    table = Table(
        title="TIMELINE CHRONOLOGIQUE MULTI-COUCHES (SW PC / DRIVER C++ / FIRMWARE MCU)",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Heure (PC)", style="dim white", width=12)
    table.add_column("Sous-Système", width=16)
    table.add_column("Niv", justify="center", width=6)
    table.add_column("Module", style="dim", width=22)
    table.add_column("Événement / Message", width=55)

    for entry in timeline:
        # Style selon sous-système
        if entry.subsystem == Subsystem.GUI_PC:
            subsys_str = "[cyan]GUI (Qt)[/cyan]"
        elif entry.subsystem == Subsystem.DRIVER_CPP:
            subsys_str = "[blue]DRIVER C++[/blue]"
        elif entry.subsystem == Subsystem.FIRMWARE_MCU:
            subsys_str = "[magenta]FW MCU[/magenta]"
        else:
            subsys_str = "[yellow]HW[/yellow]"

        # Style selon criticité
        if entry.level == LogLevel.CRITICAL:
            lvl_str = "[bold red]CRIT[/bold red]"
        elif entry.level == LogLevel.ERROR:
            lvl_str = "[red]ERR[/red]"
        elif entry.level == LogLevel.WARN:
            lvl_str = "[yellow]WARN[/yellow]"
        elif entry.level == LogLevel.DEBUG:
            lvl_str = "[dim]DBG[/dim]"
        else:
            lvl_str = "[green]INFO[/green]"

        msg = entry.message
        if rca and entry == rca.root_cause_entry:
            msg = f"[bold red blink]► [CAUSE RACINE] {msg}[/bold red blink]"
        elif entry.is_anomaly:
            msg = f"[yellow]! {msg}[/yellow]"

        table.add_row(entry.formatted_time, subsys_str, lvl_str, entry.module, msg)

    console.print(table)

    if rca:
        recs_str = "\n".join(f"  • {r}" for r in rca.recommendations)
        diag_content = (
            f"[bold red]Composant Responsable Présumé :[/bold red] [bold white]{rca.faulty_subsystem.value}[/bold white]\n"
            f"[bold red]Catégorie d'Incident :[/bold red] {rca.category}\n"
            f"[bold red]Sévérité Médicale :[/bold red] {rca.severity_level}\n\n"
            f"[bold yellow]Impact Clinique :[/bold yellow]\n{rca.clinical_impact}\n\n"
            f"[bold cyan]Synthèse Technique :[/bold cyan]\n{rca.technical_summary}\n\n"
            f"[bold green]Recommandations pour l'Équipe :[/bold green]\n{recs_str}"
        )
        console.print(
            Panel(
                diag_content,
                title="[bold red]RÉSULTAT DU DIAGNOSTIC DE CAUSE RACINE (RCA)[/bold red]",
                border_style="red",
            )
        )


def export_defect_markdown(ticket: DefectTicket, output_file: str):
    """Génère un ticket d'anomalie structuré au format Markdown pour Target Process / ALM."""
    recs_md = "\n".join(f"- {r}" for r in ticket.rca.recommendations)

    timeline_rows = ""
    for e in ticket.timeline:
        is_root = " 🚨 **[ROOT CAUSE]**" if e == ticket.rca.root_cause_entry else ""
        timeline_rows += (
            f"| `{e.formatted_time}` | `{e.subsystem.value}` | `{e.level.value}` | `{e.module}` | {e.message}{is_root} |\n"
        )

    content = f"""# [DEFECT] {ticket.title}

## 1. Métadonnées du Défaut (Target Process)
* **Composant Affecté :** `{ticket.component}`
* **Sévérité :** `{ticket.severity}`
* **Classification Risque IEC 62304 :** `{ticket.iec62304_risk_class}`
* **Statut :** Ouvert (Prêt pour Triage Pluridisciplinaire)
* **Équipes Notifiées :** Matériel, Firmware, QA Système

---

## 2. Impact Clinique & Patient
{ticket.rca.clinical_impact}

---

## 3. Analyse Technique de Cause Racine (RCA)
{ticket.rca.technical_summary}

---

## 4. Chronologie Unifiée des Événements (Corrélation Horodatée)
| Heure | Sous-Système | Niveau | Module | Message |
| :--- | :--- | :--- | :--- | :--- |
{timeline_rows}

---

## 5. Recommandations & Actions Correctives
{recs_md}

---
*Généré automatiquement par `med-log-correlator`.*
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    console.print(f"[bold green]✓ Fiche Target Process exportée avec succès :[/bold green] [cyan]{output_file}[/cyan]")
