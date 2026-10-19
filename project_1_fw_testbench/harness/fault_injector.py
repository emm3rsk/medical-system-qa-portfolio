"""
Moteur d'injection de pannes protocolaires et fuzzing pour le banc de test.
Permet d'évaluer la robustesse du firmware face aux corruptions de bus de communication.
"""

from typing import Tuple
from project_1_fw_testbench.firmware_sim import protocol
from project_1_fw_testbench.harness.client import FirmwareTestClient


class ProtocolFaultInjector:
    def __init__(self, client: FirmwareTestClient):
        self.client = client

    def send_bad_crc_frame(self, msg_id: int, payload: bytes = b"") -> protocol.Message:
        """Envoie une trame avec un CRC délibérément faussé."""
        seq = self.client._next_seq()
        correct_crc = protocol.calculate_crc8(bytes([msg_id, seq, len(payload)]) + payload)
        corrupted_crc = correct_crc ^ 0xFF

        corrupted_frame = protocol.encode_frame(
            msg_id=msg_id,
            seq_num=seq,
            payload=payload,
            override_crc=corrupted_crc,
        )
        self.client.send_raw(corrupted_frame)
        return self.client.receive_frame()

    def send_truncated_frame(self, msg_id: int, payload: bytes = b"") -> None:
        """Envoie seulement le début d'une trame sans terminaison (tronquée avant ETX)."""
        seq = self.client._next_seq()
        full_frame = protocol.encode_frame(msg_id=msg_id, seq_num=seq, payload=payload)
        truncated = full_frame[:-2]
        self.client.send_raw(truncated)

    def send_illegal_length_frame(self, msg_id: int, payload: bytes = b"") -> protocol.Message:
        """Envoie une trame où le champ longueur est supérieur au payload réel."""
        seq = self.client._next_seq()
        corrupted_frame = protocol.encode_frame(
            msg_id=msg_id,
            seq_num=seq,
            payload=payload,
            corrupt_length=len(payload) + 10,
        )
        self.client.send_raw(corrupted_frame)
        return self.client.receive_frame()

    def send_bad_delimiter_frame(self, msg_id: int) -> None:
        """Envoie des octets aléatoires sans délimiteur STX/ETX."""
        garbage = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
        self.client.send_raw(garbage)
