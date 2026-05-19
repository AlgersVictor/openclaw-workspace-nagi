"""tdx-mqtt-listener unit tests。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.alert_formatter import format_embed
from tools.discord_notifier import DiscordNotifyError, send_embed
from tools.listener import ListenerAuthError, _load_credentials


# ---------------------------------------------------------------------------
# alert_formatter
# ---------------------------------------------------------------------------

class TestAlertFormatter:
    def test_metro_alert_embed_structure(self):
        payload = {
            "Title": "板南線信義站列車延誤",
            "Description": "因設備故障，列車延誤約 10 分鐘。",
            "StartTime": "2026-05-19T10:00:00",
        }
        embed = format_embed("v2/Rail/Metro/Alert/TRTC", payload)

        assert "title" in embed
        assert "description" in embed
        assert "color" in embed
        assert "footer" in embed
        assert "fields" in embed
        assert "板南線信義站列車延誤" in embed["title"]
        assert "捷運" in embed["title"]

    def test_tra_alert_label(self):
        embed = format_embed("v3/Rail/TRA/Alert", {"Title": "西部幹線誤點", "Description": "..."})
        assert "臺鐵" in embed["title"]

    def test_bus_alert_label(self):
        embed = format_embed("v2/Bus/Alert/City/Taipei", {"Title": "公車停駛", "Description": "..."})
        assert "公車" in embed["title"]

    def test_resolved_status_green(self):
        payload = {"Title": "恢復正常", "Description": "已恢復", "Status": "false"}
        embed = format_embed("v2/Rail/Metro/Alert/TRTC", payload)
        assert embed["color"] == 3066993  # green

    def test_alert_status_red(self):
        payload = {"Title": "列車延誤", "Description": "延誤中"}
        embed = format_embed("v2/Rail/Metro/Alert/TRTC", payload)
        assert embed["color"] == 15158332  # red

    def test_non_dict_payload(self):
        embed = format_embed("v2/Rail/Metro/Alert/TRTC", "raw string payload")
        assert isinstance(embed["title"], str)
        assert isinstance(embed["description"], str)

    def test_topic_in_fields(self):
        embed = format_embed("v3/Rail/TRA/Alert", {"Title": "X", "Description": "Y"})
        topic_field = next((f for f in embed["fields"] if f["name"] == "Topic"), None)
        assert topic_field is not None
        assert "v3/Rail/TRA/Alert" in topic_field["value"]


# ---------------------------------------------------------------------------
# discord_notifier
# ---------------------------------------------------------------------------

class TestDiscordNotifier:
    def test_dry_run_no_network(self, capsys):
        embed = {"title": "Test", "description": "desc", "color": 123}
        send_embed(embed, dry_run=True)
        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "Test" in captured.out

    def test_missing_webhook_url_raises(self, monkeypatch):
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        with pytest.raises(DiscordNotifyError, match="DISCORD_WEBHOOK_URL"):
            send_embed({"title": "X"})

    def test_send_calls_urlopen(self, monkeypatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/fake/url")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 204

        with patch("tools.discord_notifier.urllib.request.urlopen", return_value=mock_resp):
            send_embed({"title": "T", "description": "D", "color": 1})


# ---------------------------------------------------------------------------
# listener credentials
# ---------------------------------------------------------------------------

class TestListenerCredentials:
    def test_missing_all_raises(self, monkeypatch):
        for k in ("TDX_MQTT_CLIENT_ID", "TDX_MQTT_USERNAME", "TDX_MQTT_PASSWORD"):
            monkeypatch.delenv(k, raising=False)
        with pytest.raises(ListenerAuthError):
            _load_credentials()

    def test_ok_credentials(self, monkeypatch):
        monkeypatch.setenv("TDX_MQTT_CLIENT_ID", "cid")
        monkeypatch.setenv("TDX_MQTT_USERNAME",  "usr")
        monkeypatch.setenv("TDX_MQTT_PASSWORD",  "pwd")
        cid, usr, pwd = _load_credentials()
        assert cid == "cid" and usr == "usr" and pwd == "pwd"
