"""Example script for the Python SDK relay server."""

import logging

from web_rpc_sdk import WebRpcServer


def main(host: str = "127.0.0.1", port: int = 9999) -> None:
    """Start the relay server with a sensible default logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    WebRpcServer(host=host, port=port).run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Server stopped by user")
