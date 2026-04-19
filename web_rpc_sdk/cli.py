"""Console entrypoints for installed package users."""

from __future__ import annotations

import logging

from .server import WebRpcServer


def run_server() -> None:
    """Launch the relay server with package-owned defaults."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    WebRpcServer().run()
