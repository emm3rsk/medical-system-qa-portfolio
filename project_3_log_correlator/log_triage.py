#!/usr/bin/env python3
"""
CLI d'investigation et d'aide au diagnostic pour systèmes d'imagerie médicale.
Ingère les logs IHM Qt, Driver C++ et Firmware MCU, aligne les chronologies,
identifie la cause racine et génère le ticket Target Process.
"""

import argparse
import os
import sys
from project_3_log_correlator.src.parsers import parse_driver_log, parse_mcu_log, parse_qt_log
from project_3_log_correlator.src.rca_engine import analyze_root_cause, build_defect_ticket
from project_3_log_correlator.src.report_generator import display_console_timeline, export_defect_markdown
from project_3_log_correlator.src.synchronizer import synchronize_and_merge


def main():
    parser = argparse.ArgumentParser(
        description="Outil de corrélation et diagnostic multi-logs pour systèmes médicaux."
    )
    parser.add_argument(
        "--app-log",
        default="project_3_log_correlator/fixtures/app_qt.log",
        help="Chemin vers le fichier journal applicatif Windows/Qt",
    )
    parser.add_argument(
        "--driver-log",
        default="project_3_log_correlator/fixtures/driver_comm.log",
        help="Chemin vers le fichier journal du pilote C++",
    )
    parser.add_argument(
        "--fw-log",
        default="project_3_log_correlator/fixtures/firmware_mcu.log",
        help="Chemin vers le fichier journal du firmware microcontrôleur",
    )
    parser.add_argument(
        "--output-defect",
        default="docs/Defect_Report_TargetProcess.md",
        help="Fichier de sortie pour la fiche de défaut Target Process",
    )

    args = parser.parse_args()

    # Vérification des fichiers
    for f in [args.app_log, args.driver_log, args.fw_log]:
        if not os.path.exists(f):
            print(f"Erreur : Le fichier journal '{f}' est introuvable.", file=sys.stderr)
            sys.exit(1)

    with open(args.app_log, "r", encoding="utf-8") as f:
        app_lines = f.readlines()
    with open(args.driver_log, "r", encoding="utf-8") as f:
        driver_lines = f.readlines()
    with open(args.fw_log, "r", encoding="utf-8") as f:
        fw_lines = f.readlines()

    # 1. Parsing
    app_entries = parse_qt_log(app_lines)
    driver_entries = parse_driver_log(driver_lines)
    fw_entries = parse_mcu_log(fw_lines)

    # 2. Synchronisation et Fusion
    timeline, offset_ms = synchronize_and_merge(app_entries, driver_entries, fw_entries)

    # 3. Analyse de Cause Racine (RCA)
    rca = analyze_root_cause(timeline)

    # 4. Affichage Console
    display_console_timeline(timeline, rca, offset_ms)

    # 5. Export Ticket Target Process
    if rca:
        ticket = build_defect_ticket(timeline, rca)
        export_defect_markdown(ticket, args.output_defect)


if __name__ == "__main__":
    main()
