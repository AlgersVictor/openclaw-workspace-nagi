"""tdx-mqtt unit tests — 用 FakeMQTTClient 取代 paho，不連外部。"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.mqtt_subscriber import subscribe
from tools.topic_registry import list_topics, resolve_topic


# ---------------------------------------------------------------------------
# Fake MQTT client — 模擬 paho.mqtt.client.Client 行為
# ---------------------------------------------------------------------------

class FakeMQTTClient:
    """最小化 paho Client 仿製，讓 mqtt_subscriber.py 可直接運作。"""

    def __init__(self, *args, **kwargs):
        self.on_connect    = None
        self.on_message    = None
        self.on_disconnect = None
        self._trigger_msg  = None   # 由工廠注入
        self._connect_rc   = 0      # 由工廠注入

    def username_pw_set(self, username, password): pass
    def tls_set(self, **kwargs): pass
    def loop_start(self): pass
    def loop_stop(self): pass
    def disconnect(self): pass
    def subscribe(self, topic, qos=1): pass

    def connect(self, host, port, keepalive=60):
        def _fire():
            time.sleep(0.05)
            from types import SimpleNamespace
            rc_obj = SimpleNamespace(value=self._connect_rc)
            if self.on_connect:
                self.on_connect(self, None, None, rc_obj, None)
            if self._trigger_msg and self.on_message and self._connect_rc == 0:
                time.sleep(0.05)
                msg = SimpleNamespace(
                    topic=self._trigger_msg["topic"],
                    payload=self._trigger_msg["payload"].encode("utf-8"),
                )
                self.on_message(self, None, msg)
        threading.Thread(target=_fire, daemon=True).start()


def _make_fake_client_factory(trigger_message=None, connect_rc=0):
    """回傳一個 callable，用作 mqtt.Client 的替代 constructor。"""
    def factory(*args, **kwargs):
        client = FakeMQTTClient(*args, **kwargs)
        client._trigger_msg = trigger_message
        client._connect_rc  = connect_rc
        return client
    return factory


def _env_ok(monkeypatch):
    monkeypatch.setenv("TDX_MQTT_CLIENT_ID", "test_cid")
    monkeypatch.setenv("TDX_MQTT_USERNAME",  "test_user")
    monkeypatch.setenv("TDX_MQTT_PASSWORD",  "test_pass")


# ---------------------------------------------------------------------------
# topic_registry
# ---------------------------------------------------------------------------

class TestTopicRegistry:
    def test_list_topics_nonempty(self):
        topics = list_topics()
        assert len(topics) > 0
        assert all("key" in t and "topic" in t and "description" in t for t in topics)

    def test_resolve_metro_alert_trtc(self):
        assert resolve_topic("metro_alert", operator="TRTC") == "v2/Rail/Metro/Alert/TRTC"

    def test_resolve_bus_alert_city(self):
        assert resolve_topic("bus_alert_city", city="Taipei") == "v2/Bus/Alert/City/Taipei"

    def test_resolve_wildcard_default(self):
        assert resolve_topic("metro_alert") == "v2/Rail/Metro/Alert/#"

    def test_resolve_unknown_key_raises(self):
        with pytest.raises(ValueError, match="未知 topic key"):
            resolve_topic("no_such_key")

    def test_resolve_tra_alert_no_placeholder(self):
        assert resolve_topic("tra_alert") == "v3/Rail/TRA/Alert"


# ---------------------------------------------------------------------------
# subscribe — auth error
# ---------------------------------------------------------------------------

class TestSubscribeAuthError:
    def test_missing_env_returns_auth_error(self, monkeypatch):
        for k in ("TDX_MQTT_CLIENT_ID", "TDX_MQTT_USERNAME", "TDX_MQTT_PASSWORD"):
            monkeypatch.delenv(k, raising=False)
        result = subscribe("v2/Rail/Metro/Alert/#", timeout=1)
        assert result["status"] == "auth_error"
        assert result["count"] == 0
        assert "error" in result

    def test_partial_env_returns_auth_error(self, monkeypatch):
        monkeypatch.setenv("TDX_MQTT_CLIENT_ID", "cid")
        monkeypatch.delenv("TDX_MQTT_USERNAME",  raising=False)
        monkeypatch.delenv("TDX_MQTT_PASSWORD",  raising=False)
        result = subscribe("v2/Rail/Metro/Alert/#", timeout=1)
        assert result["status"] == "auth_error"


# ---------------------------------------------------------------------------
# subscribe — mocked MQTT
# ---------------------------------------------------------------------------

class TestSubscribeMocked:
    def test_oneshot_receives_message(self, monkeypatch):
        _env_ok(monkeypatch)
        factory = _make_fake_client_factory(
            trigger_message={"topic": "v2/Rail/Metro/Alert/TRTC", "payload": '{"AlertID":"A1"}'}
        )
        with patch("tools.mqtt_subscriber.mqtt.Client", factory):
            result = subscribe("v2/Rail/Metro/Alert/TRTC", timeout=5, mode="oneshot")

        assert result["status"] == "ok"
        assert result["count"] == 1
        assert result["messages"][0]["payload"] == {"AlertID": "A1"}
        assert result["messages"][0]["topic"] == "v2/Rail/Metro/Alert/TRTC"

    def test_timeout_when_no_message(self, monkeypatch):
        _env_ok(monkeypatch)
        factory = _make_fake_client_factory(trigger_message=None)
        with patch("tools.mqtt_subscriber.mqtt.Client", factory):
            result = subscribe("v2/Rail/Metro/Alert/TRTC", timeout=0.4, mode="collect")

        assert result["status"] == "timeout"
        assert result["count"] == 0

    def test_connect_error_rc_nonzero(self, monkeypatch):
        _env_ok(monkeypatch)
        factory = _make_fake_client_factory(trigger_message=None, connect_rc=5)
        with patch("tools.mqtt_subscriber.mqtt.Client", factory):
            result = subscribe("v2/Rail/Metro/Alert/TRTC", timeout=2, mode="oneshot")

        assert result["status"] == "connect_error"
        assert "reason_code=5" in result.get("error", "")

    def test_connect_oserror(self, monkeypatch):
        _env_ok(monkeypatch)

        class OsErrorClient(FakeMQTTClient):
            def connect(self, host, port, keepalive=60):
                raise OSError("Network unreachable")

        with patch("tools.mqtt_subscriber.mqtt.Client", OsErrorClient):
            result = subscribe("v2/Rail/Metro/Alert/TRTC", timeout=2, mode="oneshot")

        assert result["status"] == "connect_error"
        assert "Network unreachable" in result.get("error", "")

    def test_collect_mode_gets_message(self, monkeypatch):
        _env_ok(monkeypatch)
        factory = _make_fake_client_factory(
            trigger_message={"topic": "v3/Rail/TRA/Alert", "payload": '{"type":"delay"}'}
        )
        with patch("tools.mqtt_subscriber.mqtt.Client", factory):
            result = subscribe("v3/Rail/TRA/Alert", timeout=0.5, mode="collect")

        assert result["status"] == "ok"
        assert result["count"] >= 1

    def test_result_schema_fields(self, monkeypatch):
        _env_ok(monkeypatch)
        factory = _make_fake_client_factory(trigger_message=None)
        with patch("tools.mqtt_subscriber.mqtt.Client", factory):
            result = subscribe("v2/Rail/Metro/Alert/#", timeout=0.2, mode="collect")

        for field in ("skill", "status", "topic", "messages", "count", "elapsed_seconds"):
            assert field in result, f"缺少欄位：{field}"
        assert result["skill"] == "tdx-mqtt"
        assert isinstance(result["messages"], list)
        assert isinstance(result["elapsed_seconds"], float)
