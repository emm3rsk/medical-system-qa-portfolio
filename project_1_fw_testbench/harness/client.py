"""
Client de test synchrone pour dialoguer avec le firmware et piloter le banc d'essai.
Gère les séquences de commandes, les réceptions et l'écoute d'événements asynchrones.
Supporte à la fois les connexions TCP standard et les sockets pré-connectées (socketpair IPC).
"""

import socket
import time
from typing import Optional, Tuple
from project_1_fw_testbench.firmware_sim import protocol


class FirmwareTestClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9099,
        sock: Optional[socket.socket] = None,
        timeout: float = 2.0,
    ):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = sock
        self.timeout = timeout
        self.seq_num: int = 0
        self.rx_buffer = bytearray()
        if self.sock:
            self.sock.settimeout(self.timeout)

    def connect(self, retries: int = 5, delay: float = 0.2):
        if self.sock:
            self.sock.settimeout(self.timeout)
            return

        for attempt in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.host, self.port))
                self.rx_buffer.clear()
                return
            except (ConnectionRefusedError, socket.error):
                if attempt == retries - 1:
                    raise
                time.sleep(delay)

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.sock.close()
            self.sock = None

    def _next_seq(self) -> int:
        self.seq_num = (self.seq_num + 1) & 0xFF
        return self.seq_num

    def send_raw(self, data: bytes):
        if not self.sock:
            raise ConnectionError("Client non connecté")
        self.sock.sendall(data)

    def receive_frame(self, timeout: Optional[float] = None) -> protocol.Message:
        """Lit les octets sur la socket jusqu'à obtenir un message complet ou lever TimeoutError."""
        if not self.sock:
            raise ConnectionError("Client non connecté")

        old_timeout = self.sock.gettimeout()
        if timeout is not None:
            self.sock.settimeout(timeout)

        start_time = time.monotonic()
        try:
            while True:
                # Vérifie d'abord si un message est déjà décodable dans le buffer
                if self.rx_buffer:
                    msg, consumed, err = protocol.decode_frame(bytes(self.rx_buffer))
                    if consumed > 0:
                        del self.rx_buffer[:consumed]
                    if msg:
                        return msg
                    if err is not None:
                        raise ValueError(f"Erreur de décodage trame: 0x{err:02X}")

                remaining_time = (timeout or self.timeout) - (time.monotonic() - start_time)
                if remaining_time <= 0:
                    raise TimeoutError("Délai de réception de trame dépassé")

                chunk = self.sock.recv(256)
                if not chunk:
                    raise ConnectionResetError("Connexion fermée par le serveur")
                self.rx_buffer.extend(chunk)

        finally:
            self.sock.settimeout(old_timeout)

    def send_and_receive(self, msg_id: int, payload: bytes = b"") -> protocol.Message:
        """Envoie une commande protocolaire standard et attend la réponse."""
        seq = self._next_seq()
        frame = protocol.encode_frame(msg_id=msg_id, seq_num=seq, payload=payload)
        self.send_raw(frame)
        return self.receive_frame()

    # --- Commandes Métier ---

    def ping(self) -> Tuple[int, int]:
        """Vérifie la présence du firmware. Retourne (état, active_fault_code)."""
        resp = self.send_and_receive(protocol.CMD_PING)
        if resp.msg_id != protocol.RSP_PONG or len(resp.payload) < 2:
            raise RuntimeError(f"Réponse inattendue au ping: {resp}")
        return resp.payload[0], resp.payload[1]

    def get_status(self) -> dict:
        """Interroge les registres matériels du firmware."""
        resp = self.send_and_receive(protocol.CMD_GET_STATUS)
        if resp.msg_id != protocol.RSP_ACK or len(resp.payload) < 7:
            raise RuntimeError(f"Échec get_status: {resp}")
        return {
            "state": resp.payload[0],
            "door_interlock_closed": bool(resp.payload[1]),
            "estop_active": bool(resp.payload[2]),
            "tube_overtemp": bool(resp.payload[3]),
            "active_fault": resp.payload[4],
            "angle_deg": int.from_bytes(resp.payload[5:7], byteorder="big"),
        }

    def set_position(self, angle_deg: int) -> bool:
        """Positionne le collimateur à un angle donné (0-360 deg)."""
        payload = angle_deg.to_bytes(2, byteorder="big")
        resp = self.send_and_receive(protocol.CMD_SET_POS, payload)
        return resp.msg_id == protocol.RSP_ACK

    def arm_xray(self, kv: int, ma: int, time_ms: int) -> protocol.Message:
        """Arme le générateur de rayons X avec les paramètres spécifiés."""
        payload = bytes([kv, ma]) + time_ms.to_bytes(2, byteorder="big")
        return self.send_and_receive(protocol.CMD_ARM_XRAY, payload)

    def fire_xray(self) -> protocol.Message:
        """Déclenche l'émission avec la clé de sécurité obligatoire."""
        return self.send_and_receive(protocol.CMD_FIRE_XRAY, protocol.FIRE_CONFIRM_KEY)

    def abort(self) -> protocol.Message:
        """Interrompt immédiatement toute opération en cours."""
        return self.send_and_receive(protocol.CMD_ABORT)

    def reset(self) -> protocol.Message:
        """Réinitialise le firmware après élimination d'un défaut."""
        return self.send_and_receive(protocol.CMD_RESET)

    def inject_hardware_fault(self, fault_code: int) -> protocol.Message:
        """Injecte une condition anormale sur un capteur (porte, arrêt urgence, température)."""
        return self.send_and_receive(protocol.CMD_INJECT_HW_FAULT, bytes([fault_code]))

    def wait_for_safety_trip(self, timeout: float = 1.0) -> protocol.Message:
        """Attend la notification asynchrone EVT_SAFETY_TRIP."""
        msg = self.receive_frame(timeout=timeout)
        if msg.msg_id != protocol.EVT_SAFETY_TRIP:
            raise AssertionError(f"Message inattendu au lieu de EVT_SAFETY_TRIP: {msg}")
        return msg
