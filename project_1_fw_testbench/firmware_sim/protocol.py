"""
Protocole de communication bas niveau pour équipement de radiologie dentaire.
Format de trame binaire avec contrôle d'intégrité CRC8-CCITT.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

# Constantes de cadrage
STX: int = 0x02  # Start of Frame (ASCII STX)
ETX: int = 0x03  # End of Frame (ASCII ETX)

# Identifiants de messages (Direction: Test -> FW ou FW -> Test)
CMD_PING: int = 0x01
RSP_PONG: int = 0x02
CMD_SET_POS: int = 0x10
CMD_ARM_XRAY: int = 0x11
CMD_FIRE_XRAY: int = 0x12
CMD_ABORT: int = 0x13
CMD_RESET: int = 0x14
CMD_GET_STATUS: int = 0x15
CMD_INJECT_HW_FAULT: int = 0x80

RSP_ACK: int = 0xF0
EVT_SAFETY_TRIP: int = 0xFE
RSP_NACK: int = 0xFF

# Codes d'erreur (NACK)
ERR_NONE: int = 0x00
ERR_BAD_CRC: int = 0x01
ERR_BAD_FRAME: int = 0x02
ERR_UNKNOWN_CMD: int = 0x03
ERR_ILLEGAL_STATE: int = 0x04
ERR_SAFETY_INTERLOCK: int = 0x05
ERR_TIMEOUT: int = 0x06
ERR_PARAM_OUT_OF_RANGE: int = 0x07

# Codes de défauts matériels injectables
FAULT_NONE: int = 0x00
FAULT_DOOR_OPEN: int = 0x01
FAULT_ESTOP_PRESSED: int = 0x02
FAULT_OVERTEMP: int = 0x03
FAULT_COLLIMATOR_STALL: int = 0x04

# Clé de confirmation obligatoire pour déclenchement émission
FIRE_CONFIRM_KEY: bytes = bytes([0xAA, 0x55])


def calculate_crc8(data: bytes) -> int:
    """
    Calcule le CRC-8 standard (Polynôme CCITT 0x07: x^8 + x^2 + x + 1).
    Valeur initiale 0x00.
    """
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


@dataclass
class Message:
    msg_id: int
    seq_num: int
    payload: bytes
    crc8: int

    def __repr__(self) -> str:
        return (
            f"Message(id=0x{self.msg_id:02X}, seq={self.seq_num}, "
            f"len={len(self.payload)}, payload=0x{self.payload.hex()}, crc=0x{self.crc8:02X})"
        )


def encode_frame(
    msg_id: int,
    seq_num: int,
    payload: bytes = b"",
    override_crc: Optional[int] = None,
    corrupt_length: Optional[int] = None,
) -> bytes:
    """
    Encode un message en trame binaire complète :
    [STX] [MSG_ID] [SEQ_NUM] [PAYLOAD_LEN] [PAYLOAD] [CRC8] [ETX]
    """
    payload_len = corrupt_length if corrupt_length is not None else len(payload)
    header = bytes([msg_id, seq_num, payload_len])
    body_for_crc = header + payload

    crc = override_crc if override_crc is not None else calculate_crc8(body_for_crc)
    return bytes([STX]) + header + payload + bytes([crc, ETX])


def decode_frame(buffer: bytes) -> Tuple[Optional[Message], int, Optional[int]]:
    """
    Tente de décoder la première trame valide dans un buffer d'octets.
    Retourne : (Message ou None, nombre_octets_consommés, code_erreur_si_échec)
    """
    if not buffer:
        return None, 0, None

    # Recherche du délimiteur de début STX
    stx_index = buffer.find(bytes([STX]))
    if stx_index == -1:
        # Aucun STX trouvé, on jette tout le buffer non valide
        return None, len(buffer), ERR_BAD_FRAME

    # Longueur minimale requise : STX(1) + ID(1) + SEQ(1) + LEN(1) + CRC(1) + ETX(1) = 6 octets
    if len(buffer) - stx_index < 6:
        # Trame incomplète, attente de données
        return None, stx_index, None

    frame_start = stx_index
    msg_id = buffer[frame_start + 1]
    seq_num = buffer[frame_start + 2]
    payload_len = buffer[frame_start + 3]

    expected_total_len = 1 + 3 + payload_len + 2  # STX + Header + Payload + CRC + ETX
    if len(buffer) - frame_start < expected_total_len:
        # Trame en cours de réception
        return None, frame_start, None

    payload_start = frame_start + 4
    payload_end = payload_start + payload_len
    payload = buffer[payload_start:payload_end]
    received_crc = buffer[payload_end]
    received_etx = buffer[payload_end + 1]

    if received_etx != ETX:
        # Problème de cadrage
        return None, frame_start + 1, ERR_BAD_FRAME

    # Vérification CRC8
    body_for_crc = buffer[frame_start + 1 : payload_end]
    calculated_crc = calculate_crc8(body_for_crc)

    if received_crc != calculated_crc:
        return None, frame_start + expected_total_len, ERR_BAD_CRC

    msg = Message(msg_id=msg_id, seq_num=seq_num, payload=payload, crc8=received_crc)
    return msg, frame_start + expected_total_len, None
