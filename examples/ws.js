!function() {
    // 交互数据类型
    let send_info = {
        "client_id": "",
        "callback": "",
        "method": "",
        "data": "",
        "code": "",
    };
    // 加密函数 - 以某音web端ac_signature 加密函数为例 - 你也可以替换成其他js加密函数
    function sign(ac_nonce) {
        // 自定义返回数据类型: string、json
        return window.byted_acrawler.sign("", ac_nonce)
    }
    // 注册 - 加密函数
    invoke_function = {
        'sign': sign,
    };
    // 本次web 端身份ID
    let web_id = "web1";
    let ws = null;
    let reconnectTimer = null;
    let firstDisconnectAt = null;
    let isManualClose = false;
    // 更换成你的server ip and port
    const WS_URL = "ws://127.0.0.1:9999";
    const RETRY_INTERVAL = 5000;
    const MAX_RETRY_DURATION = 60000;

    function terminateProgram() {
        console.error("WebSocket 重连超过 60s，程序终止");
        if (typeof process !== "undefined" && typeof process.exit === "function") {
            process.exit(1);
        }
        throw new Error("WebSocket reconnect timeout");
    }

    function scheduleReconnect() {
        if (isManualClose || reconnectTimer) {
            return;
        }

        if (!firstDisconnectAt) {
            firstDisconnectAt = Date.now();
        }

        if (Date.now() - firstDisconnectAt >= MAX_RETRY_DURATION) {
            terminateProgram();
            return;
        }

        reconnectTimer = setTimeout(function() {
            reconnectTimer = null;
            connectWebSocket();
        }, RETRY_INTERVAL);
    }

    function connectWebSocket() {
        ws = new WebSocket(WS_URL);

        // 建立连接 注意：client_id 应该唯一key
        ws.onopen = function() {
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            firstDisconnectAt = null;

            // 建立连接后触发 - 初始化
            send_info["client_id"] = web_id;
            send_info["callback"] = "init";
            // 返回数据
            ws.send(JSON.stringify(send_info));
        };

        ws.onmessage = function(evt) {
            // 接收服务端返回信息
            let resp_data = JSON.parse(evt.data);
            // 加密参数
            let data = resp_data['data'];
            // 指定绑定的client 的回调函数 - 由后端控制返回给对应client
            let callback = resp_data['client_id'];

            // 获取 - 加密函数名称 && 执行加密
            let value;
            let method_name = resp_data['method'] || "";
            if (data != '') {
                value = invoke_function[method_name](data);
                send_info["code"] = 200;
            } else {
                value = invoke_function[method_name]();
                send_info["code"] = 200;
            }

            send_info["client_id"] = web_id;
            send_info["callback"] = callback;
            send_info["method"] = method_name;

            // 加密结果由加密函数控制
            send_info["data"] = value;
            // 返回加密结果
            ws.send(JSON.stringify(send_info));
        };

        ws.onerror = function() {
            if (ws && ws.readyState !== WebSocket.CLOSED) {
                ws.close();
            }
        };

        ws.onclose = function() {
            scheduleReconnect();
        };
    }

    connectWebSocket();
}();
