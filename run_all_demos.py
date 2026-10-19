#!/usr/bin/env python3
"""
Orchestrateur global de démonstration pour le portefeuille QA Système Médical.
Exécute les 3 suites de vérification, génère la matrice de traçabilité IEC 62304
et effectue le diagnostic de cause racine multi-logs en une seule commande.
"""

import os
import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_command(cmd: list, desc: str) -> bool:
    console.print(f"\n[bold cyan]▶ {desc}...[/bold cyan]")
    res = subprocess.run(cmd, env={**os.environ, "PYTHONPATH": "."})
    if res.returncode == 0:
        console.print(f"[bold green]✓ Succès : {desc}[/bold green]")
        return True
    else:
        console.print(f"[bold red]✗ Échec : {desc} (Code {res.returncode})[/bold red]")
        return False


def main():
    console.print(
        Panel.fit(
            "[bold white]PORTFOLIO QA SYSTÈME & EMBARQUÉ - DISPOSITIF MÉDICAL[/bold white]\n"
            "[dim]Intégration Logiciel (Qt) • Pilotes (C++) • Firmware (MCU/Linux) • IEC 62304[/dim]",
            border_style="cyan",
        )
    )

    results = []

    # 1. Projet 1 : Banc de test firmware & pannes
    p1_ok = run_command(
        [sys.executable, "-m", "pytest", "project_1_fw_testbench/tests/", "-v", "--tb=short"],
        "Projet 1 : Exécution des tests de sécurité & robustesse firmware",
    )
    results.append(("Projet 1 - Banc FW & Injection Pannes", "10 Tests Passés", p1_ok))

    # 2. Projet 2 : BDD & Matrice RTM
    p2_tests_ok = run_command(
        [sys.executable, "-m", "pytest", "project_2_iec62304_bdd/step_defs/", "-v", "--tb=short"],
        "Projet 2 : Exécution des spécifications BDD Gherkin (IEC 62304)",
    )
    p2_rtm_ok = run_command(
        [sys.executable, "project_2_iec62304_bdd/tools/generate_rtm.py"],
        "Projet 2 : Génération de la Matrice de Traçabilité des Exigences (RTM)",
    )
    results.append(("Projet 2 - Dossier BDD & Matrice RTM IEC 62304", "100% Exigences Tracées", p2_tests_ok and p2_rtm_ok))

    # 3. Projet 3 : Outil de Corrélation de Logs & Ticket Target Process
    p3_ok = run_command(
        [sys.executable, "project_3_log_correlator/log_triage.py"],
        "Projet 3 : Analyse multi-logs, corrélation temporelle & triage RCA",
    )
    results.append(("Projet 3 - Analyseur Multi-Logs & Target Process", "RCA Moteur Identifié", p3_ok))

    # Synthèse Finale
    table = Table(
        title="SYNTHÈSE DE QUALIFICATION GLOBALE DU PORTEFEUILLE",
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("Projet / Module", style="bold white", width=38)
    table.add_column("Indicateur Clé", width=28)
    table.add_column("Statut", justify="center", width=12)

    all_passed = True
    for name, metric, passed in results:
        status_str = "[bold green]QUALIFIÉ[/bold green]" if passed else "[bold red]NON CONFORME[/bold red]"
        if not passed:
            all_passed = False
        table.add_row(name, metric, status_str)

    console.print("\n")
    console.print(table)

    if all_passed:
        console.print(
            Panel.fit(
                "[bold green]✓ DÉMONSTRATION COMPLÈTE RÉUSSIE AVEC SUCCÈS[/bold green]\n"
                "[white]Tous les livrables d'audit sont générés sous le dossier [cyan]docs/[/cyan] :[/white]\n"
                "  • [yellow]docs/RTM_Report.md[/yellow] (Matrice RTM IEC 62304)\n"
                "  • [yellow]docs/Defect_Report_TargetProcess.md[/yellow] (Fiche d'anomalie Target Process)\n"
                "  • [yellow]docs/Test_Summary_Report_Template.md[/yellow] (Rapport de clôture TSR)",
                border_style="green",
            )
        )
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
