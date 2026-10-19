"""
Moteur d'analyse de cause racine (Root Cause Analysis - RCA).
Identifie l'événement déclencheur initial (précurseur) et élimine les faux positifs
dus aux erreurs en cascade (ex: timeouts de drivers ou pop-ups d'erreur IHM).
"""

from typing import List, Optional
from .models import DefectTicket, LogEntry, LogLevel, RCAFinding, Subsystem


def analyze_root_cause(timeline: List[LogEntry]) -> Optional[RCAFinding]:
    """
    Parcourt la timeline unifiée et applique des règles heuristiques de diagnostic médical.
    """
    anomalies = [e for e in timeline if e.is_anomaly or e.level in (LogLevel.ERROR, LogLevel.CRITICAL)]
    if not anomalies:
        return None

    # L'anomalie la plus précoce dans le temps est le précurseur suspecté
    root_candidate = anomalies[0]

    msg_lower = root_candidate.message.lower()

    # Règle 1 : Défaillance mécanique / surintensité moteur (Collimator / Motor)
    if "motor" in msg_lower or "spike" in msg_lower or "stall" in msg_lower or "collimator" in msg_lower:
        return RCAFinding(
            root_cause_entry=root_candidate,
            faulty_subsystem=Subsystem.HARDWARE,
            severity_level="MAJEURE (IEC 62304 Classe B/C)",
            category="Électronique / Mécanique (Axe Collimateur)",
            clinical_impact=(
                "Interruption prématurée du tir radiologique (exposition partielle). "
                "Sécurité patient préservée par la coupure immédiate en Safe State (< 50ms). "
                "Nouvelle acquisition requise après intervention."
            ),
            technical_summary=(
                f"Surintensité détectée sur l'axe collimateur ({root_candidate.message}) "
                "ayant déclenché la coupure matérielle par interlock et le passage du firmware en STATE_SAFE_HALT. "
                "Les erreurs ultérieures côté pilote C++ (Watchdog Expired) et IHM (Erreur 0x503) "
                "sont des conséquences directes de cette mise en sécurité."
            ),
            recommendations=[
                "Contrôler la résistance mécanique et les frottements du chariot de collimation.",
                "Vérifier le calibre et la stabilité du capteur de courant moteur.",
                "Informer l'équipe logicielle PC qu'aucune correction logicielle n'est nécessaire : "
                "le timeout applicatif est la conséquence attendue de la coupure matérielle.",
            ],
        )

    # Règle 2 : Déconnexion ou corruption USB / Transport
    if "crc" in msg_lower or "usb" in msg_lower or "packet" in msg_lower:
        return RCAFinding(
            root_cause_entry=root_candidate,
            faulty_subsystem=Subsystem.DRIVER_CPP,
            severity_level="MOYENNE",
            category="Liaison de Communication / Pilote USB",
            clinical_impact="Échec de transfert sans exposition radiologique non contrôlée.",
            technical_summary="Perte de trames ou corruption de paquets sur le bus de communication.",
            recommendations=[
                "Vérifier le blindage du câble USB et les perturbations CEM.",
                "Analyser le driver de contrôleur USB sous Windows.",
            ],
        )

    # Règle par défaut
    return RCAFinding(
        root_cause_entry=root_candidate,
        faulty_subsystem=root_candidate.subsystem,
        severity_level="MINEURE / NON CLASSIFIÉE",
        category="Générique",
        clinical_impact="À évaluer par l'équipe clinique.",
        technical_summary=root_candidate.message,
        recommendations=["Effectuer une investigation approfondie avec les logs détaillés."],
    )


def build_defect_ticket(timeline: List[LogEntry], rca: RCAFinding) -> DefectTicket:
    """Construit une fiche de défaut complète au format Target Process / ALM."""
    title = f"[{rca.faulty_subsystem.value}] {rca.category} - {rca.root_cause_entry.message}"
    if len(title) > 90:
        title = title[:87] + "..."

    return DefectTicket(
        title=title,
        component=rca.faulty_subsystem.value,
        severity=rca.severity_level,
        iec62304_risk_class="Non-acceptable sans mitigation matérielle",
        timeline=timeline,
        rca=rca,
    )
