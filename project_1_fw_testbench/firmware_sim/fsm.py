"""
Machine à états finis (FSM) et gestionnaire des sécurités du firmware médical.
Conforme aux invariants de sécurité IEC 62304 Classe C pour émission de Rayons X.
"""

import time
from enum import IntEnum
from typing import List, Optional, Tuple
from project_1_fw_testbench.firmware_sim import protocol


class FirmwareState(IntEnum):
    STATE_IDLE = 0x00
    STATE_POSITIONING = 0x01
    STATE_READY = 0x02
    STATE_ARMED = 0x03
    STATE_EMITTING = 0x04
    STATE_SAFE_HALT = 0x05


class HardwareRegisters:
    def __init__(self):
        self.door_interlock_closed: bool = True
        self.estop_active: bool = False
        self.tube_overtemp: bool = False
        self.collimator_stalled: bool = False
        self.current_angle_deg: int = 0
        self.target_angle_deg: int = 0
        self.armed_kv: int = 0
        self.armed_ma: int = 0
        self.armed_time_ms: int = 0
        self.armed_timestamp: float = 0.0
        self.emission_start_time: float = 0.0
        self.active_fault_code: int = protocol.FAULT_NONE

    def are_interlocks_safe(self) -> Tuple[bool, int]:
        """Vérifie l'intégrité de tous les interlocks matériels."""
        if not self.door_interlock_closed:
            return False, protocol.FAULT_DOOR_OPEN
        if self.estop_active:
            return False, protocol.FAULT_ESTOP_PRESSED
        if self.tube_overtemp:
            return False, protocol.FAULT_OVERTEMP
        if self.collimator_stalled:
            return False, protocol.FAULT_COLLIMATOR_STALL
        return True, protocol.FAULT_NONE


class FirmwareFSM:
    def __init__(self):
        self.state: FirmwareState = FirmwareState.STATE_IDLE
        self.hw = HardwareRegisters()
        self.last_trip_reason: int = protocol.FAULT_NONE
        self.last_trip_duration_ms: float = 0.0
        self.pending_events: List[protocol.Message] = []

    @property
    def is_emitting(self) -> bool:
        return self.state == FirmwareState.STATE_EMITTING

    def pop_pending_event(self) -> Optional[protocol.Message]:
        if self.pending_events:
            return self.pending_events.pop(0)
        return None

    def tick(self) -> Optional[protocol.Message]:
        """
        Appelé périodiquement (tick temps réel).
        Vérifie les expirations de timer et surveille les interlocks en cours d'émission.
        """
        now = time.monotonic()

        # Surveillance active pendant l'armement (Timeout de 10s max sans tir)
        if self.state == FirmwareState.STATE_ARMED:
            if now - self.hw.armed_timestamp > 10.0:
                self.state = FirmwareState.STATE_READY
                return None

        # Surveillance critique pendant l'émission de Rayons X
        if self.state == FirmwareState.STATE_EMITTING:
            elapsed_ms = (now - self.hw.emission_start_time) * 1000.0

            # 1. Vérification des sécurités matérielles
            is_safe, fault_code = self.hw.are_interlocks_safe()
            if not is_safe:
                return self._trigger_safety_halt(fault_code, elapsed_ms)

            # 2. Vérification fin d'exposition nominale
            if elapsed_ms >= self.hw.armed_time_ms:
                self.state = FirmwareState.STATE_IDLE
                return None

        return None

    def _trigger_safety_halt(self, fault_code: int, emission_duration_ms: float) -> protocol.Message:
        """Bascule d'urgence immédiate en état de repli sécurisé (Safe State)."""
        self.state = FirmwareState.STATE_SAFE_HALT
        self.last_trip_reason = fault_code
        self.last_trip_duration_ms = emission_duration_ms
        self.hw.active_fault_code = fault_code

        # Génère une notification asynchrone d'arrêt d'urgence
        payload = bytes([fault_code]) + int(emission_duration_ms).to_bytes(2, byteorder="big")
        msg = protocol.Message(
            msg_id=protocol.EVT_SAFETY_TRIP,
            seq_num=0xFF,
            payload=payload,
            crc8=0,
        )
        self.pending_events.append(msg)
        return msg

    def process_command(self, msg: protocol.Message) -> Tuple[int, bytes]:
        """
        Traite un message protocolaire validé et applique les règles de transition d'état.
        """
        if self.state == FirmwareState.STATE_SAFE_HALT:
            if msg.msg_id == protocol.CMD_RESET:
                return self._handle_reset()
            elif msg.msg_id == protocol.CMD_GET_STATUS:
                return self._handle_get_status()
            elif msg.msg_id == protocol.CMD_PING:
                return protocol.RSP_PONG, bytes([self.state.value, self.hw.active_fault_code])
            elif msg.msg_id == protocol.CMD_INJECT_HW_FAULT:
                return self._handle_fault_injection(msg.payload)
            else:
                return protocol.RSP_NACK, bytes([protocol.ERR_ILLEGAL_STATE])

        if msg.msg_id == protocol.CMD_PING:
            return protocol.RSP_PONG, bytes([self.state.value, self.hw.active_fault_code])

        elif msg.msg_id == protocol.CMD_GET_STATUS:
            return self._handle_get_status()

        elif msg.msg_id == protocol.CMD_SET_POS:
            return self._handle_set_pos(msg.payload)

        elif msg.msg_id == protocol.CMD_ARM_XRAY:
            return self._handle_arm(msg.payload)

        elif msg.msg_id == protocol.CMD_FIRE_XRAY:
            return self._handle_fire(msg.payload)

        elif msg.msg_id == protocol.CMD_ABORT:
            return self._handle_abort()

        elif msg.msg_id == protocol.CMD_RESET:
            return self._handle_reset()

        elif msg.msg_id == protocol.CMD_INJECT_HW_FAULT:
            return self._handle_fault_injection(msg.payload)

        else:
            return protocol.RSP_NACK, bytes([protocol.ERR_UNKNOWN_CMD])

    def _handle_get_status(self) -> Tuple[int, bytes]:
        status_payload = bytes([
            self.state.value,
            1 if self.hw.door_interlock_closed else 0,
            1 if self.hw.estop_active else 0,
            1 if self.hw.tube_overtemp else 0,
            self.hw.active_fault_code,
        ]) + self.hw.current_angle_deg.to_bytes(2, byteorder="big")
        return protocol.RSP_ACK, status_payload

    def _handle_set_pos(self, payload: bytes) -> Tuple[int, bytes]:
        if len(payload) < 2:
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])
        if self.state not in (FirmwareState.STATE_IDLE, FirmwareState.STATE_READY):
            return protocol.RSP_NACK, bytes([protocol.ERR_ILLEGAL_STATE])

        angle = int.from_bytes(payload[0:2], byteorder="big")
        if angle > 360:
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])

        self.state = FirmwareState.STATE_POSITIONING
        self.hw.target_angle_deg = angle
        self.hw.current_angle_deg = angle
        self.state = FirmwareState.STATE_READY
        return protocol.RSP_ACK, bytes([self.state.value])

    def _handle_arm(self, payload: bytes) -> Tuple[int, bytes]:
        if len(payload) < 4:
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])

        if self.state not in (FirmwareState.STATE_IDLE, FirmwareState.STATE_READY):
            return protocol.RSP_NACK, bytes([protocol.ERR_ILLEGAL_STATE])

        is_safe, fault = self.hw.are_interlocks_safe()
        if not is_safe:
            return protocol.RSP_NACK, bytes([protocol.ERR_SAFETY_INTERLOCK])

        kv = payload[0]
        ma = payload[1]
        time_ms = int.from_bytes(payload[2:4], byteorder="big")

        if not (50 <= kv <= 90 and 1 <= ma <= 15 and 50 <= time_ms <= 5000):
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])

        self.hw.armed_kv = kv
        self.hw.armed_ma = ma
        self.hw.armed_time_ms = time_ms
        self.hw.armed_timestamp = time.monotonic()
        self.state = FirmwareState.STATE_ARMED
        return protocol.RSP_ACK, bytes([self.state.value])

    def _handle_fire(self, payload: bytes) -> Tuple[int, bytes]:
        if self.state != FirmwareState.STATE_ARMED:
            return protocol.RSP_NACK, bytes([protocol.ERR_ILLEGAL_STATE])

        if payload != protocol.FIRE_CONFIRM_KEY:
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])

        is_safe, fault = self.hw.are_interlocks_safe()
        if not is_safe:
            self.state = FirmwareState.STATE_SAFE_HALT
            return protocol.RSP_NACK, bytes([protocol.ERR_SAFETY_INTERLOCK])

        self.hw.emission_start_time = time.monotonic()
        self.state = FirmwareState.STATE_EMITTING
        return protocol.RSP_ACK, bytes([self.state.value])

    def _handle_abort(self) -> Tuple[int, bytes]:
        if self.state in (FirmwareState.STATE_ARMED, FirmwareState.STATE_EMITTING, FirmwareState.STATE_POSITIONING):
            self.state = FirmwareState.STATE_IDLE
            return protocol.RSP_ACK, bytes([self.state.value])
        return protocol.RSP_ACK, bytes([self.state.value])

    def _handle_reset(self) -> Tuple[int, bytes]:
        is_safe, fault = self.hw.are_interlocks_safe()
        if not is_safe:
            return protocol.RSP_NACK, bytes([protocol.ERR_SAFETY_INTERLOCK])

        self.state = FirmwareState.STATE_IDLE
        self.hw.active_fault_code = protocol.FAULT_NONE
        self.last_trip_reason = protocol.FAULT_NONE
        return protocol.RSP_ACK, bytes([self.state.value])

    def _handle_fault_injection(self, payload: bytes) -> Tuple[int, bytes]:
        """Permet au banc de test de manipuler l'état physique des capteurs."""
        if not payload:
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])

        fault_type = payload[0]
        if fault_type == protocol.FAULT_DOOR_OPEN:
            self.hw.door_interlock_closed = False
        elif fault_type == protocol.FAULT_ESTOP_PRESSED:
            self.hw.estop_active = True
        elif fault_type == protocol.FAULT_OVERTEMP:
            self.hw.tube_overtemp = True
        elif fault_type == protocol.FAULT_COLLIMATOR_STALL:
            self.hw.collimator_stalled = True
        elif fault_type == protocol.FAULT_NONE:
            self.hw.door_interlock_closed = True
            self.hw.estop_active = False
            self.hw.tube_overtemp = False
            self.hw.collimator_stalled = False
        else:
            return protocol.RSP_NACK, bytes([protocol.ERR_PARAM_OUT_OF_RANGE])

        # Si nous étions en émission et qu'un défaut est injecté, basculement immédiat
        if self.is_emitting and fault_type != protocol.FAULT_NONE:
            elapsed = (time.monotonic() - self.hw.emission_start_time) * 1000.0
            self._trigger_safety_halt(fault_type, elapsed)

        return protocol.RSP_ACK, bytes([self.state.value])
