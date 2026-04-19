"""Example script for the Python SDK client."""

from web_rpc_sdk import WebRpcClient


def run_client(host: str, port: int, params: str, timeout: float = 10):
    """Keep the original demo entrypoint while delegating to the SDK."""
    client = WebRpcClient(
        host=host,
        port=port,
        timeout=timeout,
        client_id="demo1111",
        callback_id="web1",
    )
    # 使用通用 call_sync，避免把 SDK 绑定到某个固定业务方法。
    return client.call_sync("sign", params).to_dict()


if __name__ == "__main__":
    sample_nonce = "069e21fae009da0d78e5b"
    result = run_client("127.0.0.1", 9999, sample_nonce)
    print(result)
