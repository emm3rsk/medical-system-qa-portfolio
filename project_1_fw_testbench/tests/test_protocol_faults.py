"""
Tests de robustesse protocolaire et injection de fautes logiques.
Vérifie la résilience du firmware face aux corruptions de trames et violations d'états.
"""

import pytest
from project_1_fw_testbench.firmware_sim import protocol
from project_1_fw_testbench.firmware_sim.fsm import FirmwareState


def test_corrupt_crc_is_rejected(fw_env):
    """Vérifie qu'une trame avec un CRC corrompu est rejetée par un RSP_NACK(ERR_BAD_CRC)."""
    injector = fw_env["injector"]
    resp = injector.send_bad_crc_frame(protocol.CMD_PING)
    assert resp.msg_id == protocol.RSP_NACK
    assert resp.payload[0] == protocol.ERR_BAD_CRC


def test_fire_without_arm_rejected(fw_env):
    """Vérifie qu'un tir direct sans armement préalable est rejeté sans déclencher d'émission."""
    client = fw_env["client"]
    resp = client.fire_xray()
    assert resp.msg_id == protocol.RSP_NACK
    assert resp.payload[0] == protocol.ERR_ILLEGAL_STATE

    # Vérification que le firmware reste sain et en IDLE
    state, fault = client.ping()
    assert state == FirmwareState.STATE_IDLE


def test_parameters_out_of_range(fw_env):
    """Vérifie le rejet de paramètres physiques non conformes aux normes radiologiques."""
    client = fw_env["client"]

    # Tension kV trop élevée (> 90 kV pour dentaire)
    resp_kv = client.arm_xray(kv=110, ma=10, time_ms=200)
    assert resp_kv.msg_id == protocol.RSP_NACK
    assert resp_kv.payload[0] == protocol.ERR_PARAM_OUT_OF_RANGE

    # Angle supérieur à 360°
    client.set_position(400)
    status = client.get_status()
    assert status["angle_deg"] != 400


def test_truncated_frame_and_recovery(fw_env):
    """Vérifie que l'envoi d'une trame incomplète n'entraîne pas de blocage du buffer de réception."""
    client = fw_env["client"]
    injector = fw_env["injector"]

    # Envoi de trame tronquée
    injector.send_truncated_frame(protocol.CMD_PING)

    # Envoi d'une commande Ping pour déclencher l'évacuation du buffer
    seq = client._next_seq()
    frame = protocol.encode_frame(msg_id=protocol.CMD_PING, seq_num=seq)
    client.send_raw(frame)

    # Réception du NACK cadrage ou de la réponse
    resp = client.receive_frame()
    assert resp.msg_id in (protocol.RSP_NACK, protocol.RSP_PONG)

    # La liaison doit être immédiatement opérationnelle pour le ping suivant
    state, fault = client.ping()
    assert state == FirmwareState.STATE_IDLE
