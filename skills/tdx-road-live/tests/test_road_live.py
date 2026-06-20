"""tdx-road-live unit tests。"""

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

from road_live_formatter import (
    format_cctv_summary,
    format_congestion_summary,
    format_live_traffic_summary,
    format_mapped_only_summary,
    format_traffic_news_summary,
)
from road_live_mapper import (
    map_cctv_payload,
    map_congestion_payload,
    map_live_traffic_payload,
    map_traffic_news_payload,
)
import road_live_query


# ---------------------------------------------------------------------------
# mapper
# ---------------------------------------------------------------------------

class TestMapLiveTrafficPayload:
    def test_extracts_fields(self):
        payload = {
            "LiveTraffics": [
                {
                    "SectionID": "S001",
                    "TravelTime": 120,
                    "TravelSpeed": 30,
                    "CongestionLevel": 2,
                    "DataCollectTime": "2026-01-01T00:00:00+08:00",
                }
            ]
        }
        items = map_live_traffic_payload(payload)
        assert len(items) == 1
        assert items[0]["section_id"] == "S001"
        assert items[0]["travel_speed"] == 30
        assert items[0]["congestion_level"] == 2

    def test_empty_payload(self):
        assert map_live_traffic_payload({}) == []

    def test_missing_fields_are_none(self):
        payload = {"LiveTraffics": [{}]}
        items = map_live_traffic_payload(payload)
        assert items[0]["section_id"] is None
        assert items[0]["travel_time"] is None


class TestMapCongestionPayload:
    def test_dict_with_key(self):
        payload = {"CongestionLevels": [{"SectionID": "S1", "CongestionLevel": 1, "CongestionLevelID": "A"}]}
        items = map_congestion_payload(payload)
        assert items[0]["section_id"] == "S1"
        assert items[0]["level_id"] == "A"

    def test_list_input(self):
        payload = [{"SectionID": "S2", "CongestionLevel": 3, "CongestionLevelID": "B"}]
        items = map_congestion_payload(payload)
        assert items[0]["congestion_level"] == 3

    def test_empty_dict(self):
        assert map_congestion_payload({}) == []


class TestMapTrafficNewsPayload:
    def test_list_input(self):
        payload = [{"Title": "施工", "Description": "封路", "PublishTime": "2026-01-01"}]
        items = map_traffic_news_payload(payload)
        assert items[0]["title"] == "施工"

    def test_newses_key(self):
        payload = {"Newses": [{"Title": "積水", "Description": "慢行", "PublishTime": "2026-01-02"}]}
        items = map_traffic_news_payload(payload)
        assert items[0]["title"] == "積水"

    def test_news_key_fallback(self):
        payload = {"News": [{"Title": "事故", "Description": "待清", "PublishTime": "2026-01-03"}]}
        items = map_traffic_news_payload(payload)
        assert items[0]["title"] == "事故"

    def test_empty(self):
        assert map_traffic_news_payload({}) == []


class TestMapCctvPayload:
    def test_dict_with_cctvs(self):
        payload = {"CCTVs": [{"CCTVID": "C1", "RoadName": "中山路", "City": "Taipei", "CCTVURL": "http://x"}]}
        items = map_cctv_payload(payload)
        assert items[0]["cctv_id"] == "C1"
        assert items[0]["url"] == "http://x"

    def test_list_input(self):
        payload = [{"CCTVID": "C2", "RoadName": "民族路", "City": "Kaohsiung", "CCTVURL": "http://y"}]
        items = map_cctv_payload(payload)
        assert items[0]["city"] == "Kaohsiung"

    def test_empty(self):
        assert map_cctv_payload({}) == []


# ---------------------------------------------------------------------------
# formatter
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_live_traffic_summary(self):
        s = format_live_traffic_summary("高雄市", 5)
        assert "高雄市" in s
        assert "5" in s

    def test_traffic_news_summary(self):
        s = format_traffic_news_summary("台北市", 3)
        assert "台北市" in s
        assert "3" in s

    def test_congestion_summary(self):
        s = format_congestion_summary("台中市", 8)
        assert "台中市" in s
        assert "8" in s

    def test_cctv_summary(self):
        s = format_cctv_summary("高雄市", 15)
        assert "高雄市" in s
        assert "15" in s

    def test_mapped_only_summary(self):
        s = format_mapped_only_summary("cctv_info", "台南市")
        assert "cctv_info" in s
        assert "台南市" in s


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------

def _fake_city_result(value="Kaohsiung", label="高雄市"):
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
        "path": "/v2/Road/Live/City/{City}",
        "validation_state": validation_state,
    }


class TestExecuteInvalidIntent:
    def test_unknown_intent_returns_invalid_input(self):
        result = road_live_query.execute({"intent": "no_such_intent"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteNeedsClarification:
    def test_no_city_triggers_clarification(self):
        with patch.object(road_live_query, "resolve_city") as mock_rc:
            mock_rc.return_value = {
                "needs_clarification": True,
                "normalized_value": None,
                "details": {"label": None, "reason": "no_city_given"},
            }
            result = road_live_query.execute({"intent": "traffic_live_summary"})
        assert result["status"] == "needs_clarification"
        assert result["needs_clarification"] is True


class TestExecuteMappedOnly:
    def test_unsupported_intent_returns_invalid_input(self):
        result = road_live_query.execute({"intent": "no_such_road_live_intent"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteCongestionLevel:
    def test_returns_congestion_items(self):
        fake_data = {"CongestionLevels": [
            {"SectionID": "S001", "CongestionLevel": 2, "CongestionLevelID": "B"},
            {"SectionID": "S002", "CongestionLevel": 3, "CongestionLevelID": "C"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute({"intent": "congestion_level", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert result["items"][0]["section_id"] == "S001"
        assert result["items"][0]["congestion_level"] == 2
        assert "壅塞" in result["summary"]


class TestExecuteTrafficNews:
    def test_returns_news_items(self):
        fake_data = [{"Title": "施工", "Description": "封閉", "PublishTime": "2026-01-01"}]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute({"intent": "traffic_news", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "施工"


class TestExecuteTrafficLiveSummary:
    def test_returns_live_traffic_items(self):
        fake_data = {"LiveTraffics": [{"SectionID": "S1", "TravelTime": 60, "TravelSpeed": 40, "CongestionLevel": 1, "DataCollectTime": "2026-01-01"}]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute({"intent": "traffic_live_summary", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1

    def test_keyword_filter(self):
        fake_data = {
            "LiveTraffics": [
                {"SectionID": "SEC-NORTH-01", "TravelTime": 60, "TravelSpeed": 40, "CongestionLevel": 1, "DataCollectTime": ""},
                {"SectionID": "SEC-SOUTH-02", "TravelTime": 90, "TravelSpeed": 20, "CongestionLevel": 3, "DataCollectTime": ""},
            ]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute(
                {"intent": "traffic_live_summary", "city": "高雄市", "keyword": "NORTH"},
                client=mock_client,
            )
        assert len(result["items"]) == 1
        assert "NORTH" in result["items"][0]["section_id"]


class TestExecuteCctvInfo:
    def test_returns_cctv_items(self):
        fake_data = {"CCTVs": [
            {"CCTVID": "C1", "RoadName": "中山路", "City": "Kaohsiung", "CCTVURL": "http://cctv1.example"},
            {"CCTVID": "C2", "RoadName": "民族路", "City": "Kaohsiung", "CCTVURL": "http://cctv2.example"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute({"intent": "cctv_info", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert result["items"][0]["cctv_id"] == "C1"
        assert "監視器" in result["summary"]

    def test_keyword_filter(self):
        fake_data = {"CCTVs": [
            {"CCTVID": "C1", "RoadName": "中山路", "City": "Kaohsiung", "CCTVURL": "http://x1"},
            {"CCTVID": "C2", "RoadName": "民族路", "City": "Kaohsiung", "CCTVURL": "http://x2"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute(
                {"intent": "cctv_info", "city": "高雄市", "keyword": "中山"},
                client=mock_client,
            )
        assert len(result["items"]) == 1
        assert result["items"][0]["cctv_id"] == "C1"


class TestExecuteErrors:
    def test_auth_error(self):
        from tdx_auth import TdxAuthError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxAuthError("token fail")
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute({"intent": "traffic_live_summary", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "auth_error"

    def test_upstream_error(self):
        from tdx_client import TdxClientError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxClientError("500 error")
        with (
            patch.object(road_live_query, "resolve_city", return_value=_fake_city_result()),
            patch.object(road_live_query, "get_endpoint", return_value=_fake_endpoint_meta()),
            patch.object(road_live_query, "build_query_options", return_value={}),
        ):
            result = road_live_query.execute({"intent": "traffic_live_summary", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "upstream_error"
