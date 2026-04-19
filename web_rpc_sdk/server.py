"""Relay server that routes messages between Python callers and browser clients."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict

import websockets
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

from .models import RpcMessage


# The relay uses an internal prefix to mark short-lived Python SDK callers.
# This is an implementation detail; end users still pass plain business ids.
LOGGER = logging.getLogger(__name__)
SHORT_LIVED_CLIENT_PREFIX = "client_id_"


class WebRpcServer:
    """
    Minimal WebSocket relay for the browser RPC workflow.

    The relay itself does not execute business logic. It only registers connected
    clients and forwards JSON protocol messages to the target callback client.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9999) -> None:
        self.host = host
        self.port = port
        self._connections: Dict[str, ServerConnection] = {}

    def _cleanup_connection(self, websocket: ServerConnection) -> None:
        """Remove all callback keys bound to a disconnected socket."""
        expired_keys = [
            key for key, conn in self._connections.items()
            if conn == websocket
        ]
        for key in expired_keys:
            self._connections.pop(key, None)

    async def _send_error(
        self,
        websocket: ServerConnection,
        *,
        code: int,
        data: str,
    ) -> None:
        """Return a protocol-compatible error response to the current client."""
        await websocket.send(
            json.dumps(
                RpcMessage(code=code, data=data).to_dict(),
                ensure_ascii=False,
            )
        )

    async def _notify_sender_target_closed(
        self,
        raw_message: str,
    ) -> None:
        """
        Notify the original sender that the target peer disconnected mid-forward.

        This keeps the relay behavior close to the original demo while making the
        cleanup explicit and easier to reason about.
        """
        data = json.loads(raw_message)
        callback_key = data.get("client_id")
        if not callback_key:
            return

        sender_socket = self._connections.get(callback_key)
        if not sender_socket:
            return

        error_message = RpcMessage.from_dict(data)
        error_message.code = 500
        error_message.message = "target websocket disconnected"
        await sender_socket.send(
            json.dumps(error_message.to_dict(), ensure_ascii=False)
        )

    async def _forward(self, raw_message: str, target_key: str) -> None:
        """Forward one raw protocol message to the registered target client."""
        target_socket = self._connections[target_key]
        try:
            await target_socket.send(raw_message)
        except (ConnectionClosedError, ConnectionClosed):
            self._connections.pop(target_key, None)
            await self._notify_sender_target_closed(raw_message)

        # Python SDK callers are short-lived per request, so once the response is
        # forwarded back we can safely release their internal routing entry.
        if target_key.startswith(SHORT_LIVED_CLIENT_PREFIX):
            self._connections.pop(target_key, None)

    async def _handle_message(
        self,
        websocket: ServerConnection,
        raw_message: str,
    ) -> None:
        """Validate a message, manage registration, and relay it if possible."""
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            await self._send_error(
                websocket,
                code=402,
                data="request data type is error, data of json!",
            )
            return

        message = RpcMessage.from_dict(payload)
        client_id = message.client_id
        callback_key = message.callback

        if not callback_key:
            await self._send_error(
                websocket,
                code=403,
                data=f"not find callback: {callback_key} of client",
            )
            return

        if callback_key == "init":
            # Browser peers use `init` to advertise their routing key.
            self._connections[client_id] = websocket
            LOGGER.info("registered client_id=%s", client_id)
            return

        if (
            client_id.startswith(SHORT_LIVED_CLIENT_PREFIX)
            and client_id not in self._connections
        ):
            # SDK callers use short-lived sockets, so the relay registers the
            # internal route lazily when the first request arrives.
            self._connections[client_id] = websocket

        if callback_key == "close":
            self._connections.pop(client_id, None)
            return

        if callback_key not in self._connections:
            await self._send_error(
                websocket,
                code=403,
                data=f"not find callback client: {callback_key}",
            )
            return

        await self._forward(raw_message, callback_key)

    async def handler(self, websocket: ServerConnection) -> None:
        """Main connection loop for each accepted WebSocket client."""
        LOGGER.info("new connection: %s", websocket.remote_address)
        try:
            while True:
                try:
                    raw_message = await websocket.recv()
                except ConnectionClosed:
                    LOGGER.info("connection closed: %s", websocket.remote_address)
                    break
                except Exception as exc:
                    LOGGER.exception("recv error from %s: %s", websocket.remote_address, exc)
                    break

                LOGGER.debug("recv data: %s", raw_message)
                await self._handle_message(websocket, raw_message)
        finally:
            self._cleanup_connection(websocket)

    async def start(self) -> None:
        """Start the relay server and block forever until cancelled."""
        server = await websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=None,
        )
        LOGGER.info("server started at ws://%s:%s", self.host, self.port)
        try:
            await asyncio.Future()
        finally:
            self._connections.clear()
            server.close()
            await server.wait_closed()

    def run(self) -> None:
        """Synchronous convenience entrypoint for scripts and demos."""
        asyncio.run(self.start())
