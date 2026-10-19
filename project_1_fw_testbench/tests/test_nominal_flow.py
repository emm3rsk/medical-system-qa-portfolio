"""
Tests nominaux (Happy Path) pour le cycle complet d'acquisition radiologique.
Vérifie les transitions d'états conformes et le positionnement du collimateur.
"""

import time
import pytest
from project_1_fw_testbench.firmware_sim import protocol
from project_1_fw_testbench.firmware_sim.fsm import FirmwareState


def test_ping_pong_liveness(fw_env):
    """Vérifie la réponse au Ping et l'état initial IDLE."""
    client = fw_env["client"]
    state, fault = client.ping()
    assert state == FirmwareState.STATE_IDLE
    assert fault == protocol.FAULT_NONE


def test_collimator_positioning(fw_env):
    """Vérifie le positionnement angulaire du collimateur."""
    client = fw_env["client"]
    # Positionnement à 180 degrés
    success = client.set_position(180)
    assert success is True

    status = client.get_status()
    assert status["angle_deg"] == 180
    assert status["state"] == FirmwareState.STATE_READY


def test_full_nominal_xray_cycle(fw_env):
    """
    Scénario nominal complet :
    1. Positionnement collimateur (90°)
    2. Armement générateur (70 kV, 8 mA, 150 ms)
    3. Déclenchement émission avec clé de sécurité
    4. Attente de fin d'exposition
    5. Retour automatique à l'état IDLE
    """
    client = fw_env["client"]

    # 1. Positionnement
    assert client.set_position(90) is True

    # 2. Armement
    resp_arm = client.arm_xray(kv=70, ma=8, time_ms=150)
    assert resp_arm.msg_id == protocol.RSP_ACK
    assert resp_arm.payload[0] == FirmwareState.STATE_ARMED

    # 3. Tir
    resp_fire = client.fire_xray()
    assert resp_fire.msg_id == protocol.RSP_ACK
    assert resp_fire.payload[0] == FirmwareState.STATE_EMITTING

    # 4. Attente fin d'exposition (150 ms + marge)
    time.sleep(0.25)

    # 5. Vérification retour à IDLE
    state, fault = client.ping()
    assert state == FirmwareState.STATE_IDLE
    assert fault == protocol.FAULT_NONE
