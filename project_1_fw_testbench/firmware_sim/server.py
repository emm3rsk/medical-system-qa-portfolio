"""
Serveur émulant le microcontrôleur embarqué temps réel.
Supporte le mode TCP standard et le mode socketpair (in-memory IPC pour tests rapides sans permissions réseau).
"""

import asyncio
import logging
import socket
from typing import Optional
from project_1_fw_testbench.firmware_sim import protocol
from project_1_fw_testbench.firmware_sim.fsm import FirmwareFSM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [FW_SIM] %(message)s")
logger = logging.getLogger("FirmwareServer")


class FirmwareServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9099,
        raw_socket: Optional[socket.socket] = None,
    ):
        self.host = host
        self.port = port
        self.raw_socket = raw_socket
        self.fsm = FirmwareFSM()
        self.server: Optional[asyncio.Server] = None
        self.active_writer: Optional[asyncio.StreamWriter] = None
        self.is_running: bool = False
        self._tick_task: Optional[asyncio.Task] = None
        self._client_task: Optional[asyncio.Task] = None

    async def start(self):
        self.is_running = True
        self._tick_task = asyncio.create_task(self._tick_loop())

        if self.raw_socket:
            reader, writer = await asyncio.open_connection(sock=self.raw_socket)
            self._client_task = asyncio.create_task(self.handle_client(reader, writer))
            logger.info("Serveur firmware démarré sur socketpair IPC.")
        else:
            self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
            logger.info(f"Serveur firmware démarré sur {self.host}:{self.port}")

    async def stop(self):
        self.is_running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass

        if self._client_task:
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass

        if self.active_writer:
            try:
                self.active_writer.close()
                await self.active_writer.wait_closed()
            except Exception:
                pass

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Serveur firmware arrêté.")

    async def _send_pending_events(self):
        if not self.active_writer:
            return
        while True:
            evt = self.fsm.pop_pending_event()
            if not evt:
                break
            frame = protocol.encode_frame(
                msg_id=evt.msg_id,
                seq_num=evt.seq_num,
                payload=evt.payload,
            )
            self.active_writer.write(frame)
            await self.active_writer.drain()
            logger.warning(f"Événement asynchrone envoyé: 0x{evt.msg_id:02X}")

    async def _tick_loop(self):
        """Boucle périodique temps-réel (10ms) pour surveiller l'état et émettre les alertes."""
        while self.is_running:
            try:
                self.fsm.tick()
                await self._send_pending_events()
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle tick: {e}")
                await asyncio.sleep(0.01)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_addr = writer.get_extra_info("peername") or "socketpair-peer"
        logger.info(f"Connexion acceptée ({client_addr})")
        self.active_writer = writer
        rx_buffer = bytearray()

        try:
            while self.is_running:
                chunk = await reader.read(256)
                if not chunk:
                    break

                rx_buffer.extend(chunk)

                # Décodage des trames dans le buffer
                while rx_buffer:
                    msg, consumed, err = protocol.decode_frame(bytes(rx_buffer))
                    if consumed > 0:
                        del rx_buffer[:consumed]

                    if err is not None:
                        logger.warning(f"Erreur protocole détectée: 0x{err:02X}")
                        resp_frame = protocol.encode_frame(
                            msg_id=protocol.RSP_NACK,
                            seq_num=0x00,
                            payload=bytes([err]),
                        )
                        writer.write(resp_frame)
                        await writer.drain()
                        continue

                    if msg is None:
                        break

                    logger.debug(f"Trame reçue: {msg}")
                    resp_id, resp_payload = self.fsm.process_command(msg)

                    resp_frame = protocol.encode_frame(
                        msg_id=resp_id,
                        seq_num=msg.seq_num,
                        payload=resp_payload,
                    )
                    writer.write(resp_frame)
                    await writer.drain()

                    # Émission immédiate de tout événement asynchrone déclenché par la commande
                    await self._send_pending_events()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Erreur client: {e}")
        finally:
            if self.active_writer == writer:
                self.active_writer = None
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def main():
    server = FirmwareServer()
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
