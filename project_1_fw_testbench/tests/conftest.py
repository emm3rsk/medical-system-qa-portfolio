"""
Fixtures PyTest pour le banc de test firmware.
Démarre et arrête automatiquement une instance propre du simulateur dans un thread dédié
en utilisant socketpair (IPC in-memory ultra-rapide et déterministe).
"""

import asyncio
import socket
import threading
import time
import pytest
from project_1_fw_testbench.firmware_sim.server import FirmwareServer
from project_1_fw_testbench.harness.client import FirmwareTestClient
from project_1_fw_testbench.harness.fault_injector import ProtocolFaultInjector


class ServerThread(threading.Thread):
    def __init__(self, raw_socket: socket.socket):
        super().__init__(daemon=True)
        self.raw_socket = raw_socket
        self.server = FirmwareServer(raw_socket=self.raw_socket)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.server.start())
        self.loop.run_forever()

    def stop(self):
        if self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.server.stop(), self.loop)
            try:
                future.result(timeout=1.0)
            except Exception:
                pass
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.join(timeout=1.0)


@pytest.fixture(scope="function")
def fw_env():
    """Démarre une instance neuve du simulateur firmware reliée par socketpair IPC."""
    server_sock, client_sock = socket.socketpair()

    server_thread = ServerThread(server_sock)
    server_thread.start()

    client = FirmwareTestClient(sock=client_sock, timeout=1.5)
    fault_injector = ProtocolFaultInjector(client)

    time.sleep(0.05)  # Petit délai pour laisser le loop asyncio initialiser la connexion

    yield {
        "client": client,
        "injector": fault_injector,
        "server": server_thread.server,
    }

    client.close()
    server_thread.stop()
    try:
        server_sock.close()
    except Exception:
        pass
