"""TDX MQTT 訂閱器。

連線 mqtt.transportdata.tw:8883（MQTTS），訂閱指定 Topic，
依 mode 決定何時回傳收到的訊息。

認證 env var（與 REST API 金鑰不同，從 TDX 會員中心取得）：
  TDX_MQTT_CLIENT_ID   — MQTT ClientId
  TDX_MQTT_USERNAME    — MQTT Username
  TDX_MQTT_PASSWORD    — MQTT Password
"""

from __future__ import annotations

import json
import os
import ssl
import threading
import time
import uuid
from typing import Any

import paho.mqtt.client as mqtt

MQTT_HOST = "mqtt.transportdata.tw"
MQTT_PORT = 8883

_ENV_CLIENT_ID = "TDX_MQTT_CLIENT_ID"
_ENV_USERNAME  = "TDX_MQTT_USERNAME"
_ENV_PASSWORD  = "TDX_MQTT_PASSWORD"


class MQTTAuthError(Exception):
    """MQTT 認證憑證缺失。"""


class MQTTConnectError(Exception):
    """MQTT 連線失敗。"""


def _load_credentials() -> tuple[str, str, str]:
    """從 env 讀取 MQTT 認證三元組 (client_id, username, password)。"""
    client_id = os.environ.get(_ENV_CLIENT_ID)
    username  = os.environ.get(_ENV_USERNAME)
    password  = os.environ.get(_ENV_PASSWORD)
    if not (client_id and username and password):
        missing = [k for k, v in {
            _ENV_CLIENT_ID: client_id,
            _ENV_USERNAME: username,
            _ENV_PASSWORD: password,
        }.items() if not v]
        raise MQTTAuthError(
            f"MQTT 認證 env var 未設定：{missing}\n"
            "請至 TDX 會員中心 → 資料服務 → 資料存取金鑰 取得 MQTT 帳號，\n"
            "並設定 TDX_MQTT_CLIENT_ID / TDX_MQTT_USERNAME / TDX_MQTT_PASSWORD。\n"
            "注意：MQTT 認證與 REST API 金鑰（TDX_CLIENT_ID/SECRET）是不同的憑證。"
        )
    return client_id, username, password


def subscribe(
    topic: str,
    *,
    timeout: float = 30.0,
    mode: str = "oneshot",
    qos: int = 1,
) -> dict[str, Any]:
    """訂閱 TDX MQTT Topic 並收集訊息。

    Args:
        topic: MQTT Topic（支援 # 萬用字元），如 v2/Rail/Metro/Alert/#
        timeout: 等待秒數（daemon mode 忽略）
        mode: oneshot（收到第一筆立即結束）| collect（等滿 timeout）| daemon（持續，需外部中斷）
        qos: 0|1|2

    Returns:
        {status, topic, messages, count, elapsed_seconds}
    """
    try:
        client_id, username, password = _load_credentials()
    except MQTTAuthError as exc:
        return _result("auth_error", topic, [], str(exc))

    messages: list[dict[str, Any]] = []
    connect_event = threading.Event()
    stop_event = threading.Event()
    connect_rc: list[int] = []

    def on_connect(client, userdata, flags, reason_code, properties):
        if hasattr(reason_code, 'value'):
            rc = reason_code.value
        else:
            rc = int(reason_code)
        connect_rc.append(rc)
        if rc == 0:
            client.subscribe(topic, qos=qos)
        connect_event.set()

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = msg.payload.decode("utf-8", errors="replace")
        messages.append({
            "topic": msg.topic,
            "payload": payload,
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        })
        if mode == "oneshot":
            stop_event.set()

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        pass

    mqttc = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        clean_session=True,
    )
    mqttc.username_pw_set(username, password)
    mqttc.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    mqttc.on_connect    = on_connect
    mqttc.on_message    = on_message
    mqttc.on_disconnect = on_disconnect

    t0 = time.monotonic()
    try:
        mqttc.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except OSError as exc:
        return _result("connect_error", topic, [], str(exc))

    mqttc.loop_start()

    # 等待連線完成
    if not connect_event.wait(timeout=15):
        mqttc.loop_stop()
        mqttc.disconnect()
        return _result("connect_error", topic, [], "連線逾時（15s）")

    rc = connect_rc[0] if connect_rc else -1
    if rc != 0:
        mqttc.loop_stop()
        mqttc.disconnect()
        return _result("connect_error", topic, [], f"連線拒絕 reason_code={rc}")

    # 等待訊息
    if mode == "daemon":
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        deadline = timeout - (time.monotonic() - t0)
        stop_event.wait(timeout=max(deadline, 0))

    mqttc.loop_stop()
    mqttc.disconnect()

    elapsed = round(time.monotonic() - t0, 2)
    status = "ok" if messages else "timeout"
    return _result(status, topic, messages, None, elapsed)


def _result(
    status: str,
    topic: str,
    messages: list,
    error: str | None,
    elapsed: float = 0.0,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "skill": "tdx-mqtt",
        "status": status,
        "topic": topic,
        "messages": messages,
        "count": len(messages),
        "elapsed_seconds": elapsed,
    }
    if error:
        out["error"] = error
    return out
