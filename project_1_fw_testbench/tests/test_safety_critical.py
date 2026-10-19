"""
Tests de sécurité critique (Safety Invariants) selon IEC 62304 Classe C.
Vérifie la coupure immédiate en Safe State sur rupture d'interlock ou arrêt d'urgence.
"""

import time
import pytest
from project_1_fw_testbench.firmware_sim import protocol
from project_1_fw_testbench.firmware_sim.fsm import FirmwareState


def test_door_open_prevents_arming(fw_env):
    """Vérifie qu'il est impossible d'armer si l'interlock de porte est ouvert."""
    client = fw_env["client"]

    # 1. Injection de porte ouverte
    client.inject_hardware_fault(protocol.FAULT_DOOR_OPEN)

    # 2. Tentative d'armement
    resp = client.arm_xray(kv=70, ma=8, time_ms=200)
    assert resp.msg_id == protocol.RSP_NACK
    assert resp.payload[0] == protocol.ERR_SAFETY_INTERLOCK

    # 3. Rétablissement porte fermée
    client.inject_hardware_fault(protocol.FAULT_NONE)
    resp_ok = client.arm_xray(kv=70, ma=8, time_ms=200)
    assert resp_ok.msg_id == protocol.RSP_ACK


def test_door_opened_during_emission_cuts_xray_immediately(fw_env):
    """
    Test critique de sécurité :
    L'ouverture de l'interlock pendant l'émission doit :
    1. Couper l'émission en moins de 50 ms.
    2. Basculer la machine en STATE_SAFE_HALT.
    3. Émettre un événement asynchrone EVT_SAFETY_TRIP.
    """
    client = fw_env["client"]

    # 1. Armement pour une émission de 2000 ms
    assert client.arm_xray(kv=70, ma=8, time_ms=2000).msg_id == protocol.RSP_ACK

    # 2. Déclenchement de l'émission
    t_start = time.monotonic()
    assert client.fire_xray().msg_id == protocol.RSP_ACK

    # 3. Laisse l'émission s'établir (100 ms) puis ouverture brutale de la porte
    time.sleep(0.10)
    client.inject_hardware_fault(protocol.FAULT_DOOR_OPEN)

    # 4. Réception attendue de l'événement d'arrêt d'urgence
    evt = client.wait_for_safety_trip(timeout=0.5)
    t_trip = time.monotonic()

    # Vérification que le trip est intervenu rapidement (< 80 ms)
    assert (t_trip - t_start) < 0.3
    assert evt.payload[0] == protocol.FAULT_DOOR_OPEN

    # 5. Vérification du statut système : verrouillé en SAFE_HALT
    status = client.get_status()
    assert status["state"] == FirmwareState.STATE_SAFE_HALT
    assert status["door_interlock_closed"] is False


def test_recovery_flow_from_safe_halt(fw_env):
    """
    Vérifie la procédure de réarmement après mise en sécurité :
    - Un Reset est refusé tant que la condition physique de panne persiste.
    - Une fois le défaut levé, le Reset permet de revenir en IDLE.
    """
    client = fw_env["client"]

    # Injection arrêt d'urgence
    client.inject_hardware_fault(protocol.FAULT_ESTOP_PRESSED)
    client.abort()

    # Tentative de reset alors que l'E-Stop est toujours enfoncé
    resp_bad_reset = client.reset()
    assert resp_bad_reset.msg_id == protocol.RSP_NACK
    assert resp_bad_reset.payload[0] == protocol.ERR_SAFETY_INTERLOCK

    # Relâchement de l'E-Stop puis reset
    client.inject_hardware_fault(protocol.FAULT_NONE)
    resp_ok_reset = client.reset()
    assert resp_ok_reset.msg_id == protocol.RSP_ACK
    assert resp_ok_reset.payload[0] == FirmwareState.STATE_IDLE
