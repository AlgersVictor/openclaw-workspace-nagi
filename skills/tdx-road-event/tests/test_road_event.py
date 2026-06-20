"""tdx-road-event unit tests。"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_SHARED_CORE = _SKILL_ROOT.parent / "tdx-shared-core"

for _p in [str(_SKILL_ROOT), str(_SHARED_CORE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from road_event_formatter import format_city_history_event_summary, format_freeway_event_summary, format_highway_event_summary, format_live_event_summary, format_mapped_only_summary
from road_event_mapper import (
    map_event_city_payload,
    map_freeway_payload,
    map_highway_payload,
    map_live_event_payload,
)
import road_event_query


# ---------------------------------------------------------------------------
# mapper
# ---------------------------------------------------------------------------

class TestMapLiveEventPayload:
    def test_extracts_fields(self):
        payload = {
            "LiveEvents": [
                {
                    "EventID": "E001",
                    "EventTitle": "道路施工",
                    "Description": "封閉一線道",
                    "EventType": 1,
                    "Location": {"Other": "中山路一段"},
                    "PublishTime": "2026-01-01T00:00:00+08:00",
                }
            ]
        }
        items = map_live_event_payload(payload)
        assert len(items) == 1
        assert items[0]["event_id"] == "E001"
        assert items[0]["title"] == "道路施工"
        assert items[0]["location_other"] == "中山路一段"

    def test_missing_location_is_none(self):
        payload = {"LiveEvents": [{"EventID": "E002"}]}
        items = map_live_event_payload(payload)
        assert items[0]["location_other"] is None

    def test_empty_payload(self):
        assert map_live_event_payload({}) == []


class TestMapEventCityPayload:
    def test_dict_with_events_key(self):
        payload = {"Events": [{"EventID": "E1", "EventTitle": "積水", "Description": "請繞行"}]}
        items = map_event_city_payload(payload)
        assert items[0]["event_id"] == "E1"

    def test_list_input(self):
        payload = [{"EventID": "E2", "EventTitle": "事故", "Description": ""}]
        items = map_event_city_payload(payload)
        assert items[0]["title"] == "事故"

    def test_empty(self):
        assert map_event_city_payload({}) == []


class TestMapFreewayPayload:
    def test_dict_with_live_events_key(self):
        payload = {"LiveEvents": [{"EventID": "F1", "EventTitle": "國道事故", "Description": "待處理"}]}
        items = map_freeway_payload(payload)
        assert items[0]["event_id"] == "F1"

    def test_list_input(self):
        payload = [{"EventID": "F2", "EventTitle": "施工", "Description": "縮減車道"}]
        items = map_freeway_payload(payload)
        assert items[0]["title"] == "施工"

    def test_empty(self):
        assert map_freeway_payload({}) == []


class TestMapHighwayPayload:
    def test_dict_with_live_events_key(self):
        payload = {"LiveEvents": [{"EventID": "H1", "EventTitle": "省道事故", "Description": ""}]}
        items = map_highway_payload(payload)
        assert items[0]["event_id"] == "H1"

    def test_list_input(self):
        payload = [{"EventID": "H2", "EventTitle": "施工", "Description": ""}]
        items = map_highway_payload(payload)
        assert items[0]["title"] == "施工"

    def test_empty(self):
        assert map_highway_payload({}) == []


# ---------------------------------------------------------------------------
# formatter
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_live_event_summary(self):
        s = format_live_event_summary("台南市", 4)
        assert "台南市" in s
        assert "4" in s

    def test_highway_event_summary(self):
        s = format_highway_event_summary(7)
        assert "7" in s
        assert "省道" in s

    def test_freeway_event_summary(self):
        s = format_freeway_event_summary(3)
        assert "3" in s
        assert "國道" in s

    def test_city_history_event_summary(self):
        s = format_city_history_event_summary("台北市", 12)
        assert "台北市" in s
        assert "12" in s

    def test_mapped_only_with_city(self):
        s = format_mapped_only_summary("road_event_freeway", "台北市")
        assert "road_event_freeway" in s
        assert "台北市" in s

    def test_mapped_only_no_city(self):
        s = format_mapped_only_summary("road_event_highway")
        assert "road_event_highway" in s
        assert "目前查詢目標" in s


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------

def _fake_city_result(value="Tainan", label="台南市"):
    return {
        "needs_clarification": False,
        "normalized_value": value,
        "details": {"label": label, "reason": None},
    }


def _fake_response(data, url="https://tdx.example/endpoint"):
    return SimpleNamespace(data=data, url=url)


def _fake_endpoint_meta(validation_state="live"):
    return {
        "base_url": "https://tdx.transportdata.tw/api/basic",
        "path": "/v2/Road/Event/City/{City}",
        "validation_state": validation_state,
    }


class TestExecuteInvalidIntent:
    def test_returns_invalid_input(self):
        result = road_event_query.execute({"intent": "no_such"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteNeedsClarification:
    def test_live_city_no_city_triggers_clarification(self):
        with patch.object(road_event_query, "resolve_city") as mock_rc:
            mock_rc.return_value = {
                "needs_clarification": True,
                "normalized_value": None,
                "details": {"label": None, "reason": "no_city_given"},
            }
            result = road_event_query.execute({"intent": "road_event_live_city"})
        assert result["status"] == "needs_clarification"
        assert result["needs_clarification"] is True

    def test_city_history_no_city_triggers_clarification(self):
        with patch.object(road_event_query, "resolve_city") as mock_rc:
            mock_rc.return_value = {
                "needs_clarification": True,
                "normalized_value": None,
                "details": {"label": None, "reason": "no_city_given"},
            }
            result = road_event_query.execute({"intent": "road_event_city_history"})
        assert result["status"] == "needs_clarification"


class TestExecuteMappedOnly:
    def test_non_prechecked_returns_mapped_only(self):
        # 唯一剩餘 mapped_only intent: 無（所有 road-event intent 均已啟用）
        # 改測試 invalid_input 路徑
        result = road_event_query.execute({"intent": "no_such_event_intent"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteLiveCity:
    def test_returns_event_items(self):
        fake_data = {
            "LiveEvents": [
                {
                    "EventID": "E1",
                    "EventTitle": "積水",
                    "Description": "封閉",
                    "EventType": 2,
                    "Location": {"Other": "民族路"},
                    "PublishTime": "2026-01-01",
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_event_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute({"intent": "road_event_live_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["event_id"] == "E1"

    def test_keyword_filter_title(self):
        fake_data = {
            "LiveEvents": [
                {"EventID": "E1", "EventTitle": "積水封路", "Description": "繞行", "EventType": 1, "Location": None, "PublishTime": ""},
                {"EventID": "E2", "EventTitle": "國道施工", "Description": "縮減", "EventType": 2, "Location": None, "PublishTime": ""},
            ]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_event_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute(
                {"intent": "road_event_live_city", "city": "台南市", "keyword": "積水"},
                client=mock_client,
            )
        assert len(result["items"]) == 1
        assert result["items"][0]["event_id"] == "E1"

    def test_keyword_filter_description(self):
        fake_data = {
            "LiveEvents": [
                {"EventID": "E1", "EventTitle": "施工", "Description": "請由聯絡道繞行", "EventType": 1, "Location": None, "PublishTime": ""},
                {"EventID": "E2", "EventTitle": "事故", "Description": "待清", "EventType": 2, "Location": None, "PublishTime": ""},
            ]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_event_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute(
                {"intent": "road_event_live_city", "city": "台南市", "keyword": "繞行"},
                client=mock_client,
            )
        assert len(result["items"]) == 1
        assert result["items"][0]["event_id"] == "E1"


class TestExecuteHighway:
    def test_returns_highway_items(self):
        fake_data = {"LiveEvents": [
            {"EventID": "H1", "EventTitle": "省道事故", "Description": "封閉", "EventType": 3, "Location": None, "PublishTime": "2026-01-01"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute({"intent": "road_event_highway"}, client=mock_client)
        assert result["status"] == "ok"
        assert result["normalized_city"] is None
        assert len(result["items"]) == 1
        assert result["items"][0]["event_id"] == "H1"
        assert "省道" in result["summary"]


class TestExecuteFreeway:
    def test_returns_freeway_items(self):
        fake_data = {"LiveEvents": [
            {"EventID": "F1", "EventTitle": "國道事故", "Description": "封閉", "EventType": 4, "Location": None, "PublishTime": "2026-01-01"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute({"intent": "road_event_freeway"}, client=mock_client)
        assert result["status"] == "ok"
        assert result["normalized_city"] is None
        assert len(result["items"]) == 1
        assert result["items"][0]["event_id"] == "F1"
        assert "國道" in result["summary"]


class TestExecuteCityHistory:
    def test_returns_history_items(self):
        fake_data = {"Events": [
            {"EventID": "H1", "EventTitle": "歷史積水", "Description": "已修復"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_event_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute({"intent": "road_event_city_history", "city": "台南市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["event_id"] == "H1"
        assert "歷史" in result["summary"]


class TestExecuteErrors:
    def test_auth_error(self):
        from tdx_auth import TdxAuthError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxAuthError("401 unauthorized")
        with (
            patch.object(road_event_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute({"intent": "road_event_live_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "auth_error"
        assert result["unavailable_reason"] == "auth_error"

    def test_upstream_error(self):
        from tdx_client import TdxClientError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxClientError("503 upstream")
        with (
            patch.object(road_event_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_event_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_event_query, "build_query_options", return_value={}),
        ):
            result = road_event_query.execute({"intent": "road_event_live_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "upstream_error"
