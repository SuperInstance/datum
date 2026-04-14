"""
superagent.bus — TCP message bus for cross-machine agent communication.

The core MessageBus (in core.py) handles in-process pub/sub. This module
adds TCP networking for agents on different machines within the SuperInstance.

Messages are newline-delimited JSON over TCP. Each connection handles
one message at a time. The TCP bus bridges to the in-process bus.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Any, Callable, Dict, Optional

from datum_runtime.superagent.core import AgentMessage, MessageType


class TCPBusServer:
    """
    TCP socket server for cross-machine agent communication.

    Accepts newline-delimited JSON AgentMessages, routes them through
    the in-process bus, and returns delivery confirmation.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 7743,
                 on_message: Optional[Callable[[AgentMessage], int]] = None):
        self.host = host
        self.port = port
        self._on_message = on_message  # Callback: receives AgentMessage, returns delivered count
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._logger = logging.getLogger("bus.tcp.server")

    def start(self) -> None:
        """Start the TCP bus in a background thread."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(16)
        self._server_socket.settimeout(1.0)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        self._logger.info(f"TCP bus listening on {self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._server_socket:
            self._server_socket.close()
        if self._thread:
            self._thread.join(timeout=5)

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, addr = self._server_socket.accept()
                threading.Thread(target=self._handle, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle(self, conn: socket.socket, addr) -> None:
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            if not data.strip():
                conn.close()
                return

            raw = data.split(b"\n", 1)[0].decode().strip()
            msg = AgentMessage.from_dict(json.loads(raw))
            self._logger.debug(f"TCP: {msg.sender} -> {msg.recipient}: {msg.subject}")

            delivered = 0
            if self._on_message:
                delivered = self._on_message(msg)

            response = json.dumps({"delivered": delivered}) + "\n"
            conn.sendall(response.encode())
        except Exception as e:
            self._logger.error(f"TCP error from {addr}: {e}")
        finally:
            conn.close()


class TCPBusClient:
    """TCP client for sending messages to a remote bus."""

    def __init__(self, host: str = "localhost", port: int = 7743):
        self.host = host
        self.port = port
        self._logger = logging.getLogger("bus.tcp.client")

    def send(self, message: AgentMessage, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Send a message to the TCP bus server.

        Returns {"delivered": int, "error": Optional[str]}.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.host, self.port))
            payload = message.to_json() + "\n"
            sock.sendall(payload.encode())

            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\n" in response:
                    break
            sock.close()

            raw = response.split(b"\n", 1)[0].decode().strip()
            return json.loads(raw)
        except Exception as e:
            self._logger.error(f"TCP send error: {e}")
            return {"delivered": 0, "error": str(e)}
