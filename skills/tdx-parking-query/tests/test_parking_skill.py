"""tdx-parking-query unit tests。"""

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

from parking_formatter import (
    format_carpark_summary,
    format_keyword_filtered_summary,
    format_mapped_only_summary,
    format_offstreet_availability_summary,
)
from parking_mapper import (
    map_offstreet_availability_payload,
    map_offstreet_carpark_payload,
    map_offstreet_spot_payload,
    map_onstreet_segment_payload,
)
import parking_query


# ---------------------------------------------------------------------------
# mapper
# ---------------------------------------------------------------------------

class TestMapOffstreetAvailability:
    def test_dict_with_key(self):
        payload = {"ParkingAvailabilities": [
            {"CarParkID": "P001", "CarParkName": {"Zh_tw": "府前停車場"}, "TotalSpaces": 100, "AvailableSpaces": 30,
             "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "2026-01-01", "Address": "台南市中西區"}
        ]}
        items = map_offstreet_availability_payload(payload)
        assert items[0]["car_park_id"] == "P001"
        assert items[0]["car_park_name"] == "府前停車場"
        assert items[0]["available_spaces"] == 30

    def test_list_input(self):
        payload = [{"CarParkID": "P002", "CarParkName": "火車站停車場", "TotalSpaces": 50, "AvailableSpaces": 10,
                    "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "", "Address": ""}]
        items = map_offstreet_availability_payload(payload)
        assert items[0]["car_park_name"] == "火車站停車場"

    def test_empty(self):
        assert map_offstreet_availability_payload({}) == []

    def test_skips_non_dict_rows(self):
        payload = {"ParkingAvailabilities": ["not_a_dict", {"CarParkID": "P003", "CarParkName": "A", "TotalSpaces": 10, "AvailableSpaces": 5, "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "", "Address": ""}]}
        items = map_offstreet_availability_payload(payload)
        assert len(items) == 1


class TestMapOffstreetCarpark:
    def test_dict_with_key(self):
        payload = {"CarParks": [
            {"CarParkID": "P001", "CarParkName": {"Zh_tw": "府前"}, "Address": "台南市",
             "CarParkPosition": {"PositionLat": 23.0, "PositionLon": 120.2},
             "Description": "地下停車場", "FareDescription": "30分10元", "ServiceTime": "24hr", "ChargingStation": False}
        ]}
        items = map_offstreet_carpark_payload(payload)
        assert items[0]["car_park_id"] == "P001"
        assert items[0]["latitude"] == 23.0

    def test_list_input(self):
        payload = [{"CarParkID": "P002", "CarParkName": "轉運站", "Address": "", "CarParkPosition": {}, "Description": "", "FareDescription": "", "ServiceTime": "", "ChargingStation": None}]
        items = map_offstreet_carpark_payload(payload)
        assert items[0]["car_park_id"] == "P002"

    def test_empty(self):
        assert map_offstreet_carpark_payload({}) == []


class TestMapOnstreetSegment:
    def test_dict_with_key(self):
        payload = {"ParkingSegmentAvailabilities": [
            {"ParkingSegmentID": "S001", "RoadName": "中正路", "AvailableSpaces": 5, "ServiceStatus": 1, "DataCollectTime": "2026-01-01"}
        ]}
        items = map_onstreet_segment_payload(payload)
        assert items[0]["segment_id"] == "S001"
        assert items[0]["road_name"] == "中正路"

    def test_list_input(self):
        payload = [{"ParkingSegmentID": "S002", "RoadName": "民族路", "AvailableSpaces": 2, "ServiceStatus": 1, "DataCollectTime": ""}]
        items = map_onstreet_segment_payload(payload)
        assert items[0]["available_spaces"] == 2

    def test_empty(self):
        assert map_onstreet_segment_payload({}) == []


class TestMapOffstreetSpot:
    def test_dict_with_key(self):
        payload = {"ParkingSpotAvailabilities": [
            {"CarParkID": "P001", "CarParkName": {"Zh_tw": "府前"}, "AvailableSpaces": 3, "SpotType": 1, "ServiceStatus": 1, "DataCollectTime": "2026-01-01"}
        ]}
        items = map_offstreet_spot_payload(payload)
        assert items[0]["car_park_id"] == "P001"
        assert items[0]["spot_type"] == 1

    def test_empty(self):
        assert map_offstreet_spot_payload({}) == []


# ---------------------------------------------------------------------------
# formatter
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_offstreet_availability_no_filter(self):
        s = format_offstreet_availability_summary("台南市", 5)
        assert "台南市" in s and "5" in s

    def test_offstreet_availability_with_keyword(self):
        s = format_offstreet_availability_summary("台南市", 3, keyword="府前")
        assert "府前" in s

    def test_offstreet_availability_with_landmark(self):
        s = format_offstreet_availability_summary("台南市", 2, landmark="火車站")
        assert "火車站" in s

    def test_carpark_summary_no_keyword(self):
        s = format_carpark_summary("高雄市", 10)
        assert "高雄市" in s and "10" in s

    def test_carpark_summary_with_keyword(self):
        s = format_carpark_summary("高雄市", 4, keyword="左營")
        assert "左營" in s

    def test_keyword_filtered_summary(self):
        s = format_keyword_filtered_summary("台北市", "台北車站", 7, "offstreet_availability_city")
        assert "台北車站" in s and "7" in s

    def test_mapped_only_summary(self):
        s = format_mapped_only_summary("onstreet_segment_availability_city", "台北市", "mapped_only")
        assert "mapped_only" in s


# ---------------------------------------------------------------------------
# execute() helpers
# ---------------------------------------------------------------------------

def _city_ok(value="Tainan", label="台南市"):
    return {"needs_clarification": False, "normalized_value": value, "details": {"label": label, "reason": None}}

def _city_missing():
    return {"needs_clarification": True, "normalized_value": None, "details": {"label": None, "reason": "no_city_given"}}

def _endpoint_meta(state="prechecked"):
    return {"base_url": "https://tdx.transportdata.tw/api/basic", "path": "/v1/Parking/OffStreet/ParkingAvailability/City/{City}", "validation_state": state}

def _fake_response(data, url="https://tdx.example/parking"):
    return SimpleNamespace(data=data, url=url)


# ---------------------------------------------------------------------------
# execute() tests
# ---------------------------------------------------------------------------

class TestExecuteInvalidIntent:
    def test_unknown_intent(self):
        result = parking_query.execute({"intent": "no_such"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteNeedsClarification:
    def test_no_city(self):
        with patch.object(parking_query, "resolve_city", return_value=_city_missing()):
            result = parking_query.execute({"intent": "offstreet_availability_city"})
        assert result["status"] == "needs_clarification"
        assert result["needs_clarification"] is True

    def test_keyword_search_no_keyword(self):
        with patch.object(parking_query, "resolve_city", return_value=_city_ok()):
            result = parking_query.execute({"intent": "parking_keyword_search", "city": "台南市"})
        assert result["status"] == "needs_clarification"
        assert result["unavailable_reason"] == "keyword_required"

    def test_nearby_no_keyword_or_landmark(self):
        with patch.object(parking_query, "resolve_city", return_value=_city_ok()):
            result = parking_query.execute({"intent": "nearby_parking_summary", "city": "台南市"})
        assert result["status"] == "needs_clarification"
        assert result["unavailable_reason"] == "keyword_or_landmark_required"


class TestExecuteMappedOnly:
    def test_onstreet_segment_mapped_only(self):
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta("mapped_only")),
        ):
            result = parking_query.execute({"intent": "onstreet_segment_availability_city", "city": "台南市"})
        assert result["status"] == "ok"
        assert "phase_2d" in result["unavailable_reason"]

    def test_offstreet_spot_mapped_only(self):
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta("mapped_only")),
        ):
            result = parking_query.execute({"intent": "offstreet_spot_availability_city", "city": "台南市"})
        assert result["status"] == "ok"
        assert result["items"] == []


class TestExecuteOffstreetAvailability:
    def _fake_data(self):
        return {"ParkingAvailabilities": [
            {"CarParkID": "P001", "CarParkName": {"Zh_tw": "府前停車場"}, "TotalSpaces": 100, "AvailableSpaces": 30,
             "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "2026-01-01", "Address": "台南市中西區府前路"},
            {"CarParkID": "P002", "CarParkName": {"Zh_tw": "民族停車場"}, "TotalSpaces": 50, "AvailableSpaces": 5,
             "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "2026-01-01", "Address": "台南市中西區民族路"},
        ]}

    def test_returns_items(self):
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(self._fake_data())
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(parking_query, "build_query_options", return_value={}),
        ):
            result = parking_query.execute({"intent": "offstreet_availability_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2

    def test_keyword_filter(self):
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(self._fake_data())
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(parking_query, "build_query_options", return_value={}),
        ):
            result = parking_query.execute({"intent": "offstreet_availability_city", "city": "台南市", "keyword": "府前"}, client=mock_client)
        assert len(result["items"]) == 1
        assert result["items"][0]["car_park_id"] == "P001"


class TestExecuteNearbyParking:
    def test_landmark_filter(self):
        fake_data = {"ParkingAvailabilities": [
            {"CarParkID": "P001", "CarParkName": {"Zh_tw": "火車站停車場"}, "TotalSpaces": 80, "AvailableSpaces": 20,
             "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "", "Address": "台南市東區台南車站旁"},
            {"CarParkID": "P002", "CarParkName": {"Zh_tw": "東門停車場"}, "TotalSpaces": 60, "AvailableSpaces": 10,
             "ServiceStatus": 1, "FullStatus": 0, "ChargeStatus": 1, "DataCollectTime": "", "Address": "台南市東區東門路"},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(parking_query, "build_query_options", return_value={}),
        ):
            result = parking_query.execute({"intent": "nearby_parking_summary", "city": "台南市", "landmark": "火車站"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["car_park_id"] == "P001"


class TestExecuteKeywordSearch:
    def test_carpark_mode(self):
        fake_data = {"CarParks": [
            {"CarParkID": "P001", "CarParkName": {"Zh_tw": "左營火車站停車場"}, "Address": "高雄市左營區", "CarParkPosition": {}, "Description": "", "FareDescription": "", "ServiceTime": "", "ChargingStation": None},
        ]}
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok("Kaohsiung", "高雄市")),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(parking_query, "build_query_options", return_value={}),
        ):
            result = parking_query.execute({
                "intent": "parking_keyword_search",
                "city": "高雄市",
                "keyword": "左營",
            }, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1


class TestExecuteErrors:
    def test_auth_error(self):
        from tdx_auth import TdxAuthError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxAuthError("401")
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(parking_query, "build_query_options", return_value={}),
        ):
            result = parking_query.execute({"intent": "offstreet_availability_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "auth_error"

    def test_upstream_error(self):
        from tdx_client import TdxClientError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxClientError("503")
        with (
            patch.object(parking_query, "resolve_city", return_value=_city_ok()),
            patch.object(parking_query, "get_endpoint", return_value=_endpoint_meta()),
            patch.object(parking_query, "build_query_options", return_value={}),
        ):
            result = parking_query.execute({"intent": "offstreet_availability_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "upstream_error"
