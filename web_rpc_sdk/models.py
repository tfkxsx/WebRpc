"""Protocol models shared by the client and relay server."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(slots=True)
class RpcMessage:
    """Represents the JSON payload exchanged over the WebSocket channel."""

    client_id: str = ""
    callback: str = ""
    method: str = ""
    data: Any = ""
    code: int = 200
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message into a dict and drop empty optional fields."""
        payload = asdict(self)
        if not self.message:
            payload.pop("message")
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RpcMessage":
        """Build a protocol object from any compatible mapping."""
        return cls(
            client_id=payload.get("client_id", ""),
            callback=payload.get("callback", ""),
            method=payload.get("method", ""),
            data=payload.get("data", ""),
            code=payload.get("code", 200),
            message=payload.get("message", ""),
        )
