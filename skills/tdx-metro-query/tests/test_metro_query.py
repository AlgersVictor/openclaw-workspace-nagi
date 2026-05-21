"""tdx-metro-query unit tests。"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_SHARED_CORE = _SKILL_ROOT.parent / "tdx-shared-core"

for _p in [str(_SKILL_ROOT), str(_SHARED_CORE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from metro_formatter import (
    format_liveboard_summary,
    format_mapped_only_summary,
    format_station_summary,
)
from metro_mapper import map_liveboard_payload, map_station_payload
import metro_query


# ---------------------------------------------------------------------------
# mapper
# ---------------------------------------------------------------------------

class TestMapStationPayload:
    def test_extracts_fields(self):
        payload = [
            {
                "StationID": "BL01",
                "StationName": {"Zh_tw": "頂埔", "En": "Dingpu"},
                "StationAddress": "新北市土城區...",
                "StationPosition": {"PositionLat": 24.97, "PositionLon": 121.43},
            }
        ]
        items = map_station_payload(payload)
        assert len(items) == 1
        assert items[0]["station_id"] == "BL01"
        assert items[0]["station_name"] == "頂埔"
        assert items[0]["station_name_en"] == "Dingpu"
        assert items[0]["latitude"] == 24.97

    def test_empty_payload(self):
        assert map_station_payload([]) == []

    def test_missing_nested_fields_are_none(self):
        items = map_station_payload([{}])
        assert items[0]["station_id"] is None
        assert items[0]["station_name"] is None


class TestMapLiveboardPayload:
    def test_extracts_fields(self):
        payload = [
            {
                "LineID": "BL",
                "StationID": "BL12",
                "StationName": {"Zh_tw": "西門", "En": "Ximen"},
                "TripHeadSign": "頂埔",
                "DestinationStationName": {"Zh_tw": "頂埔"},
                "EstimateTime": 120,
                "ServiceStatus": 0,
            }
        ]
        items = map_liveboard_payload(payload)
        assert items[0]["line_id"] == "BL"
        assert items[0]["station_name"] == "西門"
        assert items[0]["estimate_time"] == 120

    def test_empty(self):
        assert map_liveboard_payload([]) == []


# ---------------------------------------------------------------------------
# formatter
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_station_summary(self):
        s = format_station_summary("TRTC", "西門", 2)
        assert "TRTC" in s and "西門" in s and "2" in s

    def test_liveboard_summary(self):
        s = format_liveboard_summary("TRTC", "台北車站", 5)
        assert "台北車站" in s and "5" in s

    def test_mapped_only_with_station(self):
        s = format_mapped_only_summary("frequency", "TRTC", "西門")
        assert "frequency" in s and "TRTC" in s and "西門" in s

    def test_mapped_only_no_station(self):
        s = format_mapped_only_summary("route_info", "KRTC")
        assert "指定站點" in s


# ---------------------------------------------------------------------------
# execute() helpers
# ---------------------------------------------------------------------------

def _rail_ok(value="TRTC"):
    return {"needs_clarification": False, "normalized_value": value, "candidates": [], "details": {"reason": None}}

def _rail_missing():
    return {"needs_clarification": True, "normalized_value": None, "candidates": [], "details": {"reason": "missing_rail_system"}}

def _station_ok(value="西門"):
    return {"needs_clarification": False, "normalized_value": value, "candidates": [], "details": {"reason": None}}

def _station_missing():
    return {"needs_clarification": True, "normalized_value": None, "candidates": [], "details": {"reason": "station_not_found"}}

def _endpoint_meta(path="/v2/Rail/Metro/Station/{RailSystem}", state="live"):
    return {"base_url": "https://tdx.transportdata.tw/api/basic", "path": path, "validation_state": state}

def _fake_response(data, url="https://tdx.example/metro"):
    return SimpleNamespace(data=data, url=url)


# ---------------------------------------------------------------------------
# execute() tests
# ---------------------------------------------------------------------------

class TestExecuteInvalidInput:
    def test_empty_intent(self):
        result = metro_query.execute({})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "missing_intent"

    def test_unsupported_intent(self):
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
        ):
            result = metro_query.execute({"intent": "no_such", "rail_system": "TRTC", "station_name": "西門"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteNeedsClarification:
    def test_missing_rail_system(self):
        with patch.object(metro_query, "resolve_rail_system", return_value=_rail_missing()):
            result = metro_query.execute({"intent": "station_info"})
        assert result["status"] == "needs_clarification"
        assert result["needs_clarification"] is True

    def test_missing_station(self):
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_missing()),
        ):
            result = metro_query.execute({"intent": "station_info", "rail_system": "TRTC"})
        assert result["status"] == "needs_clarification"

    def test_s2s_missing_destination(self):
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
        ):
            result = metro_query.execute({"intent": "s2s_travel_time", "rail_system": "TRTC", "station_name": "西門"})
        assert result["status"] == "needs_clarification"
        assert result["unavailable_reason"] == "destination_station_required"


class TestExecuteMappedOnly:
    def test_frequency_returns_mapped_only(self):
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/Frequency/{RailSystem}", "mapped_only")),
        ):
            result = metro_query.execute({"intent": "frequency", "rail_system": "TRTC", "station_name": "西門"})
        assert result["status"] == "ok"
        assert result["unavailable_reason"] == "mapped_only_phase_2a"

    def test_s2s_with_destination_returns_mapped_only(self):
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/S2STravelTime/{RailSystem}", "mapped_only")),
        ):
            result = metro_query.execute({
                "intent": "s2s_travel_time",
                "rail_system": "TRTC",
                "station_name": "西門",
                "destination_station": "台北車站",
            })
        assert result["unavailable_reason"] == "mapped_only_phase_2a"


class TestExecuteStationInfo:
    def test_returns_matched_station(self):
        fake_data = [
            {"StationID": "BL12", "StationName": {"Zh_tw": "西門", "En": "Ximen"}, "StationAddress": "台北市中正區", "StationPosition": {"PositionLat": 25.04, "PositionLon": 121.50}},
            {"StationID": "BL13", "StationName": {"Zh_tw": "台北車站", "En": "Taipei Main"}, "StationAddress": "台北市中正區", "StationPosition": {"PositionLat": 25.04, "PositionLon": 121.51}},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok("西門")),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "station_info", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["station_name"] == "西門"

    def test_no_match_returns_empty_items(self):
        fake_data = [
            {"StationID": "BL13", "StationName": {"Zh_tw": "台北車站", "En": "Taipei Main"}, "StationAddress": "", "StationPosition": {}},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok("西門")),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "station_info", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "ok"
        assert result["items"] == []


class TestExecuteLiveboard:
    def test_returns_matched_liveboard(self):
        fake_data = [
            {"LineID": "BL", "StationID": "BL12", "StationName": {"Zh_tw": "西門"}, "TripHeadSign": "頂埔", "DestinationStationName": {"Zh_tw": "頂埔"}, "EstimateTime": 60, "ServiceStatus": 0},
            {"LineID": "BL", "StationID": "BL13", "StationName": {"Zh_tw": "台北車站"}, "TripHeadSign": "南港展覽館", "DestinationStationName": {"Zh_tw": "南港展覽館"}, "EstimateTime": 120, "ServiceStatus": 0},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok("西門")),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/LiveBoard/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "liveboard", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["station_name"] == "西門"

    def test_empty_liveboard_falls_back_to_frequency(self):
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response([])
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok("西門")),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/LiveBoard/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "liveboard", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "ok"
        assert result["intent"] == "frequency"
        assert "降級" in result["summary"]


class TestExecuteErrors:
    def test_auth_error(self):
        from tdx_auth import TdxAuthError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxAuthError("401")
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "station_info", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "auth_error"

    def test_upstream_error(self):
        from tdx_client import TdxClientError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxClientError("503")
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "station_info", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "upstream_error"
