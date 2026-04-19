"""Python client for calling browser-side RPC functions through the relay server."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Optional

import websockets

from .models import RpcMessage


@dataclass(slots=True)
class ClientConfig:
    """Resolved connection settings used internally by :class:`WebRpcClient`."""

    host: str = "127.0.0.1"
    port: int = 9999
    client_id: str = "client_id_default"
    callback_id: str = "web1"
    timeout: float = 10.0

    @property
    def url(self) -> str:
        """Build the target WebSocket URL from host and port."""
        return f"ws://{self.host}:{self.port}"


def normalize_client_id(client_id: str) -> str:
    """
    Convert a user-facing client id into the relay's internal routing format.

    Callers only need to provide their own business identifier. The SDK adds the
    internal prefix required by the relay so this implementation detail does not
    leak into normal usage.
    """
    prefix = "client_id_"
    if client_id.startswith(prefix):
        return client_id
    return f"{prefix}{client_id}"


class WebRpcClient:
    """High-level SDK client for calling browser registered methods."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9999,
        *,
        client_id: str = "default",
        callback_id: str = "web1",
        timeout: float = 10.0,
    ) -> None:
        # `client_id` stays user-facing at the API boundary; normalization happens
        # once here so the rest of the SDK can work with a stable relay format.
        self.config = ClientConfig(
            host=host,
            port=port,
            client_id=normalize_client_id(client_id),
            callback_id=callback_id,
            timeout=timeout,
        )

    async def call(
        self,
        method: str,
        data: Any = "",
        *,
        timeout: Optional[float] = None,
        callback_id: Optional[str] = None,
    ) -> RpcMessage:
        """
        Call a browser-side method and wait for the response.

        The relay protocol is request/response over a single WebSocket round trip,
        so each SDK call opens a dedicated connection and closes it after receiving
        the browser result. `callback_id` remains fully user-defined and points to
        whichever browser client registered that routing key.
        """
        message = RpcMessage(
            client_id=self.config.client_id,
            callback=callback_id or self.config.callback_id,
            method=method,
            data=data,
            code=200,
        )
        return await self._send_message(message, timeout=timeout)

    async def _send_message(
        self,
        message: RpcMessage,
        *,
        timeout: Optional[float] = None,
    ) -> RpcMessage:
        """
        Send one protocol message and parse the server reply.

        `proxy=None` is intentional because local WebSocket relays often fail when
        the runtime auto-detects a corporate or system proxy.
        """
        effective_timeout = self.config.timeout if timeout is None else timeout
        async with websockets.connect(
            self.config.url,
            ping_interval=None,
            proxy=None,
        ) as websocket:
            await websocket.send(json.dumps(message.to_dict(), ensure_ascii=False))
            try:
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                await websocket.close()
                return RpcMessage(
                    client_id=message.client_id,
                    callback=message.callback,
                    method=message.method,
                    data=f"websocket recv timeout after {effective_timeout}s",
                    code=408,
                    message="request timed out",
                )

        return RpcMessage.from_dict(json.loads(response))

    def call_sync(
        self,
        method: str,
        data: Any = "",
        *,
        timeout: Optional[float] = None,
        callback_id: Optional[str] = None,
    ) -> RpcMessage:
        """Synchronous helper for scripts that do not manage an event loop."""
        return asyncio.run(
            self.call(
                method,
                data,
                timeout=timeout,
                callback_id=callback_id,
            )
        )
