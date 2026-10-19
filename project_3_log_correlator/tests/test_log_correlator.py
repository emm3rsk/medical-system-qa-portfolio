"""
Tests unitaires et d'intégration pour le corrélateur de logs et le moteur RCA.
"""

import os
import pytest
from project_3_log_correlator.src.models import LogLevel, Subsystem
from project_3_log_correlator.src.parsers import parse_driver_log, parse_mcu_log, parse_qt_log
from project_3_log_correlator.src.rca_engine import analyze_root_cause, build_defect_ticket
from project_3_log_correlator.src.synchronizer import synchronize_and_merge

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_parse_qt_log():
    sample = [
        "2026-10-17 14:15:02.100 [INFO] [UIThread] AcqWorkflow - Click exposition",
        "2026-10-17 14:15:05.310 [ERROR] [CommThread] DeviceProxy - TIMEOUT: No packet",
    ]
    entries = parse_qt_log(sample)
    assert len(entries) == 2
    assert entries[0].subsystem == Subsystem.GUI_PC
    assert entries[0].level == LogLevel.INFO
    assert entries[1].level == LogLevel.ERROR
    assert entries[1].is_anomaly is True


def test_parse_driver_log():
    sample = [
        "[14:15:02.152] [1204:4512] [USB_IO] TX -> 02 11 05 04 C8 03",
        "[14:15:05.305] [1204:4512] [USB_IO] Watchdog Expired: No packet",
    ]
    entries = parse_driver_log(sample)
    assert len(entries) == 2
    assert entries[0].subsystem == Subsystem.DRIVER_CPP
    assert entries[1].level == LogLevel.ERROR


def test_parse_mcu_log():
    sample = [
        "[T+00902155] [COMM] RX: CMD_ARM_XRAY",
        "[T+00902475] [MOTOR] WARN: Collimator step motor current spike detected (1.75A)",
    ]
    entries = parse_mcu_log(sample)
    assert len(entries) == 2
    assert entries[0].subsystem == Subsystem.FIRMWARE_MCU
    assert entries[1].is_anomaly is True


def test_full_correlation_and_rca_identifies_motor_stall():
    """
    Test d'intégration complet :
    Vérifie que parmi les 3 flux de logs, le moteur RCA isole bien
    le surcourant moteur (collimator current spike) comme la cause racine première,
    et non le timeout applicatif intervenu 3 secondes plus tard.
    """
    with open(os.path.join(FIXTURES_DIR, "app_qt.log"), "r") as f:
        app_entries = parse_qt_log(f.readlines())
    with open(os.path.join(FIXTURES_DIR, "driver_comm.log"), "r") as f:
        driver_entries = parse_driver_log(f.readlines())
    with open(os.path.join(FIXTURES_DIR, "firmware_mcu.log"), "r") as f:
        mcu_entries = parse_mcu_log(f.readlines())

    timeline, offset = synchronize_and_merge(app_entries, driver_entries, mcu_entries)

    # 1. Vérification que la timeline est chronologiquement triée
    for i in range(len(timeline) - 1):
        assert timeline[i].timestamp_abs_ms <= timeline[i + 1].timestamp_abs_ms

    # 2. Analyse RCA
    rca = analyze_root_cause(timeline)
    assert rca is not None
    assert rca.faulty_subsystem == Subsystem.HARDWARE
    assert "Axe Collimateur" in rca.category
    assert "current spike" in rca.root_cause_entry.message

    # 3. Création du ticket de bug
    ticket = build_defect_ticket(timeline, rca)
    assert ticket.component == "MATÉRIEL"
    assert "MAJEURE" in ticket.severity
