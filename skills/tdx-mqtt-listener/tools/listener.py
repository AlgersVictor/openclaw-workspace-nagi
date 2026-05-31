"""TDX MQTT 持續監聽器。

訂閱指定 Topic，收到訊息後送 Discord Embed。
斷線自動重連。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import ssl
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

_TZ_8 = timezone(timedelta(hours=8))
_DEDUP_FILE = (
    __import__("pathlib").Path.home()
    / ".openclaw/workspace/runtime/tdx/mqtt_dedup_state.json"
)
_DEDUP_TTL = timedelta(hours=2)


def _dedup_fingerprint(topic: str, payload_str: str) -> str:
    raw = f"{topic}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _dedup_load() -> dict[str, str]:
    if not _DEDUP_FILE.exists():
        return {}
    try:
        data = json.loads(_DEDUP_FILE.read_text(encoding="utf-8"))
        cutoff = datetime.now(_TZ_8) - _DEDUP_TTL
        return {
            fp: ts
            for fp, ts in data.get("fingerprints", {}).items()
            if datetime.fromisoformat(ts) > cutoff
        }
    except Exception:
        return {}


def _dedup_save(seen: dict[str, str]) -> None:
    _DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DEDUP_FILE.write_text(
        json.dumps({"fingerprints": seen}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

import paho.mqtt.client as mqtt

from tools.alert_formatter import format_embed
from tools.discord_notifier import DiscordNotifyError, send_embed

MQTT_HOST = "mqtt.transportdata.tw"
MQTT_PORT = 8883

_ENV_CLIENT_ID = "TDX_MQTT_CLIENT_ID"
_ENV_USERNAME  = "TDX_MQTT_USERNAME"
_ENV_PASSWORD  = "TDX_MQTT_PASSWORD"

logger = logging.getLogger("tdx-mqtt-listener")


class ListenerAuthError(Exception):
    pass


def _load_credentials() -> tuple[str, str, str]:
    client_id = os.environ.get(_ENV_CLIENT_ID)
    username  = os.environ.get(_ENV_USERNAME)
    password  = os.environ.get(_ENV_PASSWORD)
    if not (client_id and username and password):
        missing = [k for k, v in {
            _ENV_CLIENT_ID: client_id,
            _ENV_USERNAME:  username,
            _ENV_PASSWORD:  password,
        }.items() if not v]
        raise ListenerAuthError(f"MQTT 認證 env var 未設定：{missing}")
    return client_id, username, password


def run(
    topics: list[str],
    *,
    reconnect_delay: float = 30.0,
    qos: int = 1,
    dry_run: bool = False,
) -> None:
    """啟動持續監聽迴圈（阻塞，直到 KeyboardInterrupt）。"""
    client_id, username, password = _load_credentials()

    def _make_client() -> mqtt.Client:
        mqttc = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=True,
        )
        mqttc.username_pw_set(username, password)
        mqttc.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        return mqttc

    def on_connect(client, userdata, flags, reason_code, properties):
        rc = reason_code.value if hasattr(reason_code, "value") else int(reason_code)
        if rc == 0:
            logger.info("MQTT 連線成功，訂閱 %s", topics)
            for t in topics:
                client.subscribe(t, qos=qos)
        else:
            logger.error("MQTT 連線拒絕 rc=%s", rc)

    def on_message(client, userdata, msg):
        payload_str = msg.payload.decode("utf-8", errors="replace")
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            payload = payload_str

        fp = _dedup_fingerprint(msg.topic, payload_str)
        with seen_lock:
            if fp in seen:
                logger.debug("略過重複訊息：%s fp=%s", msg.topic, fp)
                return
            seen[fp] = datetime.now(_TZ_8).isoformat()
            _dedup_save(seen)

        logger.info("收到訊息：%s", msg.topic)
        embed = format_embed(msg.topic, payload)
        try:
            send_embed(embed, dry_run=dry_run)
        except DiscordNotifyError as exc:
            logger.error("Discord 通知失敗：%s", exc)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        logger.warning("MQTT 斷線，%s 秒後重連", reconnect_delay)

    logger.info("監聽器啟動，topics=%s dry_run=%s", topics, dry_run)
    seen: dict[str, str] = _dedup_load()
    seen_lock = threading.Lock()

    while True:
        mqttc = _make_client()
        mqttc.on_connect    = on_connect
        mqttc.on_message    = on_message
        mqttc.on_disconnect = on_disconnect
        try:
            mqttc.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            mqttc.loop_forever()
        except OSError as exc:
            logger.error("連線失敗：%s", exc)
        except KeyboardInterrupt:
            logger.info("收到中斷信號，關閉監聽器")
            mqttc.disconnect()
            break

        logger.info("等待 %s 秒後重連", reconnect_delay)
        time.sleep(reconnect_delay)
