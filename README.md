# web-rpc-sdk

`web-rpc-sdk` 是一个轻量级的 Python SDK，用来通过 WebSocket 中转服务调用浏览器端已注册的 JavaScript 方法。

它适合这类场景：

- 浏览器页面里已经有现成的加密逻辑或风控逻辑
- Python 侧只想通过稳定协议去调用浏览器函数
- 需要一个简单、可复用、可发布到 PyPI 的 SDK 形态

设计目标：

- SDK 只提供通用 RPC 调用能力，不绑定某个固定方法名
- 浏览器端可以自由注册任意方法，例如 `sign`、`encrypt`、`get_token`
- Python 侧可以自由指定 `client_id` 和目标 `callback_id`

项目包含四部分：

- `web_rpc_sdk`：可发布的 Python SDK
- `examples/`：示例目录，提供最小可运行的 client / server / browser 端脚本
- `LICENSE`：项目许可证
- `pyproject.toml`：打包与发布配置

## 安装

本地开发安装：

```bash
pip install -e .
```

安装发布包后使用：

```bash
pip install web-rpc-sdk
```

## 协议说明

WebSocket 传输的数据是 JSON 字符串，核心字段如下：

```json
{
  "client_id": "demo",
  "callback": "web1",
  "method": "your_method",
  "data": {"example": "payload"},
  "code": 200
}
```

字段含义：

- `client_id`：当前发送方的标识
- `callback`：目标客户端标识
- `method`：要调用的浏览器函数名
- `data`：函数输入参数
- `code`：状态码
- `message`：可选错误信息

默认错误码：

- `402`：请求体不是合法 JSON
- `403`：目标客户端不存在
- `408`：客户端等待响应超时
- `500`：目标端在转发时断开

## 快速开始

### 1. 启动中转服务

```bash
python examples/server.py
```

或在代码里启动：

```python
from web_rpc_sdk import WebRpcServer

WebRpcServer(host="127.0.0.1", port=9999).run()
```

### 2. 浏览器端注册函数

将 `examples/ws.js` 注入到目标页面，并根据你的实际业务注册方法。

下面的 `sign` 只是一个示例，你也可以注册 `encrypt`、`get_token` 或其他任意方法：

```javascript
function sign(ac_nonce) {
    return window.byted_acrawler.sign("", ac_nonce);
}
```

浏览器端连接成功后会通过 `callback = "init"` 注册自己，例如 `web1`。

### 3. Python 侧调用浏览器函数

同步调用：

```python
from web_rpc_sdk import WebRpcClient

client = WebRpcClient(
    host="127.0.0.1",
    port=9999,
    client_id="demo",
    callback_id="web1",
)
result = client.call_sync("your_method", {"example": "payload"})
print(result.to_dict())
```

如果你想直接运行仓库里的示例脚本：

```bash
python examples/client.py
```

异步调用：

```python
import asyncio

from web_rpc_sdk import WebRpcClient


async def main():
    client = WebRpcClient(
        host="127.0.0.1",
        port=9999,
        client_id="demo",
        callback_id="web1",
    )
    result = await client.call("your_method", {"example": "payload"})
    print(result.to_dict())


asyncio.run(main())
```

## SDK API

### `RpcMessage`

协议对象，负责在 Python 中表示 WebSocket 传输的数据。

```python
from web_rpc_sdk import RpcMessage

message = RpcMessage(
    client_id="demo",
    callback="web1",
    method="your_method",
    data="demo",
)
```

### `WebRpcClient`

`WebRpcClient` 只提供通用调用能力，推荐统一使用 `call` 或 `call_sync`。

主要方法：

- `await client.call(method, data="", timeout=None, callback_id=None)`
- `client.call_sync(method, data="", timeout=None, callback_id=None)`

示例：

```python
client.call_sync("sign", "069e21fae009da0d78e5b")
client.call_sync("encrypt", {"text": "hello"})
client.call_sync("get_token")
```

初始化参数：

- `host`：中转服务地址，默认 `127.0.0.1`
- `port`：中转服务端口，默认 `9999`
- `client_id`：当前 Python 调用方标识，传入你自己的业务标识即可，SDK 会在内部处理路由所需格式
- `callback_id`：目标浏览器客户端标识，默认 `web1`
- `timeout`：等待响应超时时间，默认 `10s`

### `WebRpcServer`

主要用法：

```python
from web_rpc_sdk import WebRpcServer

server = WebRpcServer(host="127.0.0.1", port=9999)
server.run()
```

它只做路由转发，不负责业务逻辑执行。

## 示例目录

`examples/` 当前作为示例目录使用，便于快速验证完整链路：

- `examples/server.py`：启动 WebSocket 中转服务
- `examples/client.py`：演示 Python 侧如何发起调用
- `examples/ws.js`：演示浏览器端如何注册方法并回传结果

如果后续你准备补真正的自动化测试，建议把单元测试文件放到 `tests/test_*.py`，让 `examples/` 和 `tests/` 各自只承担一种职责。


## 项目结构

```text
web-RPC/
├── LICENSE
├── README.md
├── examples
│   ├── client.py
│   ├── server.py
│   └── ws.js
├── pyproject.toml
└── web_rpc_sdk
    ├── __init__.py
    ├── cli.py
    ├── client.py
    ├── models.py
    └── server.py
```

## 注意事项

- 当前协议默认是单参数透传，如果浏览器函数需要复杂参数，建议直接传 `dict` 或 `list`
- Python SDK 客户端默认按短连接请求处理，请求结束后服务端会清理对应映射
- `ws.js` 里已经加入断线重连逻辑：每 5 秒重试一次，最多 60 秒

## License

本项目当前使用 [GNU GPL v3.0](/Users/tf/Documents/worke/lingjiang/test/web-RPC/LICENSE)。
