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
    format_frequency_summary,
    format_liveboard_summary,
    format_route_summary,
    format_s2s_summary,
    format_station_summary,
    format_station_timetable_summary,
    format_transfer_summary,
)
from metro_mapper import (
    map_frequency_payload,
    map_liveboard_payload,
    map_route_payload,
    map_s2s_travel_time_payload,
    map_station_payload,
    map_station_timetable_payload,
    map_transfer_station_payload,
)
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


class TestMapFrequencyPayload:
    def test_list_input(self):
        payload = [{"LineID": "BL", "PeakHeadway": 5, "OffPeakHeadway": 8}]
        items = map_frequency_payload(payload)
        assert items[0]["line_id"] == "BL"
        assert items[0]["peak_headway"] == 5

    def test_dict_with_frequencies_key(self):
        payload = {"Frequencies": [{"LineID": "BR", "PeakHeadway": 6}]}
        items = map_frequency_payload(payload)
        assert items[0]["line_id"] == "BR"

    def test_empty(self):
        assert map_frequency_payload({}) == []


class TestMapS2STravelTimePayload:
    def test_list_input(self):
        payload = [{"FromStationID": "BL12", "ToStationID": "BL13", "RunTime": 2}]
        items = map_s2s_travel_time_payload(payload)
        assert items[0]["from_station_id"] == "BL12"
        assert items[0]["run_time"] == 2

    def test_dict_with_key(self):
        payload = {"S2STravelTimes": [{"FromStationID": "BL14", "ToStationID": "BL15", "RunTime": 3}]}
        items = map_s2s_travel_time_payload(payload)
        assert items[0]["to_station_id"] == "BL15"

    def test_empty(self):
        assert map_s2s_travel_time_payload({}) == []


class TestMapRoutePayload:
    def test_list_input(self):
        payload = [{
            "LineID": "BL", "LineNo": "BL", "RouteID": "BL-1",
            "RouteName": {"Zh_tw": "頂埔－南港展覽館"}, "Direction": 0,
            "StartStationName": {"Zh_tw": "頂埔"}, "EndStationName": {"Zh_tw": "南港展覽館"},
            "TravelTime": 48,
        }]
        items = map_route_payload(payload)
        assert items[0]["line_id"] == "BL"
        assert items[0]["route_name"] == "頂埔－南港展覽館"
        assert items[0]["start_station"] == "頂埔"
        assert items[0]["end_station"] == "南港展覽館"
        assert items[0]["travel_time"] == 48

    def test_dict_with_routes_key(self):
        payload = {"Routes": [{"LineID": "BR", "RouteID": "BR-1"}]}
        items = map_route_payload(payload)
        assert items[0]["line_id"] == "BR"
        assert items[0]["start_station"] is None

    def test_empty(self):
        assert map_route_payload({}) == []


class TestMapStationTimetablePayload:
    def test_list_input(self):
        payload = [{
            "StationID": "BL12", "StationName": {"Zh_tw": "西門"}, "LineID": "BL",
            "Direction": 0, "DestinationStationName": {"Zh_tw": "頂埔"},
            "Timetables": [{"DepartureTime": "06:00"}, {"DepartureTime": "06:05"}],
        }]
        items = map_station_timetable_payload(payload)
        assert items[0]["station_name"] == "西門"
        assert items[0]["direction"] == 0
        assert items[0]["timetable_count"] == 2

    def test_dict_with_key(self):
        payload = {"StationTimeTables": [{"StationID": "BL13", "StationName": {"Zh_tw": "台北車站"}}]}
        items = map_station_timetable_payload(payload)
        assert items[0]["station_id"] == "BL13"
        assert items[0]["timetable_count"] == 0

    def test_empty(self):
        assert map_station_timetable_payload({}) == []


class TestMapTransferStationPayload:
    def test_list_input(self):
        payload = [{
            "SystemID": "KRTC", "TransferStationID": "O5_R10",
            "Stations": [
                {"StationID": "O5", "StationName": "美麗島"},
                {"StationID": "R10", "StationName": "美麗島"},
            ],
        }]
        items = map_transfer_station_payload(payload)
        assert items[0]["transfer_station_id"] == "O5_R10"
        assert items[0]["system_id"] == "KRTC"
        assert len(items[0]["stations"]) == 2
        assert items[0]["stations"][0]["station_id"] == "O5"
        assert items[0]["stations"][1]["station_name"] == "美麗島"

    def test_dict_with_key(self):
        payload = {"TransferStations": [{"TransferStationID": "X_Y", "Stations": []}]}
        items = map_transfer_station_payload(payload)
        assert items[0]["transfer_station_id"] == "X_Y"
        assert items[0]["stations"] == []

    def test_empty(self):
        assert map_transfer_station_payload({}) == []


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

    def test_frequency_summary(self):
        s = format_frequency_summary("TRTC", 3)
        assert "TRTC" in s and "3" in s

    def test_s2s_summary(self):
        s = format_s2s_summary("KRTC", 10)
        assert "KRTC" in s and "10" in s

    def test_route_summary(self):
        s = format_route_summary("TRTC", 5)
        assert "TRTC" in s and "5" in s

    def test_station_timetable_summary(self):
        s = format_station_timetable_summary("TRTC", "西門", 12)
        assert "TRTC" in s and "西門" in s and "12" in s

    def test_transfer_summary(self):
        s = format_transfer_summary("KRTC", 4)
        assert "KRTC" in s and "4" in s


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


class TestExecuteRouteInfo:
    def test_returns_route_items(self):
        fake_data = [
            {"LineID": "BL", "RouteID": "BL-1", "RouteName": {"Zh_tw": "頂埔－南港展覽館"},
             "StartStationName": {"Zh_tw": "頂埔"}, "EndStationName": {"Zh_tw": "南港展覽館"}, "TravelTime": 48},
            {"LineID": "R", "RouteID": "R-1", "RouteName": {"Zh_tw": "象山－淡水"},
             "StartStationName": {"Zh_tw": "象山"}, "EndStationName": {"Zh_tw": "淡水"}, "TravelTime": 50},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/Route/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "route_info", "rail_system": "TRTC"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert result["items"][0]["route_name"] == "頂埔－南港展覽館"
        assert result["items"][0]["start_station"] == "頂埔"
        assert "路線" in result["summary"]


class TestExecuteStationTimetable:
    def test_returns_filtered_timetable(self):
        fake_data = [
            {"StationID": "BL12", "StationName": {"Zh_tw": "西門"}, "LineID": "BL", "Direction": 0,
             "Timetables": [{"DepartureTime": "06:00"}]},
            {"StationID": "BL13", "StationName": {"Zh_tw": "台北車站"}, "LineID": "BL", "Direction": 0,
             "Timetables": [{"DepartureTime": "06:02"}]},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok("西門")),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/StationTimeTable/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "station_timetable", "rail_system": "TRTC", "station_name": "西門"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["station_name"] == "西門"
        assert result["items"][0]["timetable_count"] == 1

    def test_missing_station_needs_clarification(self):
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_missing()),
        ):
            result = metro_query.execute({"intent": "station_timetable", "rail_system": "TRTC"})
        assert result["status"] == "needs_clarification"


class TestExecuteTransferStations:
    def test_returns_transfer_items(self):
        fake_data = [
            {"SystemID": "KRTC", "TransferStationID": "O5_R10",
             "Stations": [{"StationID": "O5", "StationName": "美麗島"}, {"StationID": "R10", "StationName": "美麗島"}]},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok("KRTC")),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/TransferStations/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "transfer_stations", "rail_system": "KRTC"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["transfer_station_id"] == "O5_R10"
        assert len(result["items"][0]["stations"]) == 2
        assert "轉乘" in result["summary"]


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

    def test_empty_liveboard_returns_ok_no_items(self):
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
        assert result["items"] == []


class TestMetroFrequency:
    def test_returns_frequency_items(self):
        fake_data = [
            {"LineID": "BL", "PeakHeadway": 5, "OffPeakHeadway": 8},
            {"LineID": "BR", "PeakHeadway": 6, "OffPeakHeadway": 10},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/Frequency/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "frequency", "rail_system": "TRTC"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert result["items"][0]["line_id"] == "BL"
        assert result["items"][0]["peak_headway"] == 5
        assert "班距" in result["summary"]


class TestMetroS2S:
    def test_returns_s2s_items(self):
        fake_data = [
            {"FromStationID": "BL12", "ToStationID": "BL13", "RunTime": 2},
            {"FromStationID": "BL12", "ToStationID": "BL14", "RunTime": 4},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/S2STravelTime/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute({"intent": "s2s_travel_time", "rail_system": "TRTC"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert "旅行時間" in result["summary"]

    def test_destination_filter(self):
        fake_data = [
            {"FromStationID": "BL12", "ToStationID": "BL13", "RunTime": 2},
            {"FromStationID": "BL12", "ToStationID": "BL20", "RunTime": 10},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(metro_query, "resolve_rail_system", return_value=_rail_ok()),
            patch.object(metro_query, "resolve_station_alias", return_value=_station_ok()),
            patch.object(metro_query, "get_endpoint", return_value=_endpoint_meta("/v2/Rail/Metro/S2STravelTime/{RailSystem}")),
            patch.object(metro_query, "build_query_options", return_value={}),
        ):
            result = metro_query.execute(
                {"intent": "s2s_travel_time", "rail_system": "TRTC", "destination_station": "BL13"},
                client=mock_client,
            )
        assert len(result["items"]) == 1
        assert result["items"][0]["to_station_id"] == "BL13"


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
