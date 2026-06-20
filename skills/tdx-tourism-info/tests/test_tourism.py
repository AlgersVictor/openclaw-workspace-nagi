"""tdx-tourism-info unit tests。"""

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

from tourism_formatter import (
    format_keyword_filtered_summary,
    format_mapped_only_summary,
    format_restaurant_summary,
    format_scenic_spot_summary,
)
from tourism_mapper import (
    map_activity_payload,
    map_hotel_payload,
    map_restaurant_payload,
    map_scenic_spot_payload,
    map_attraction_payload_v21,
    map_cycling_route_payload_v21,
    map_event_payload_v21,
    map_hotel_payload_v21,
    map_restaurant_payload_v21,
    map_trail_payload_v21,
)
from geocode_fallback import (
    is_geocode_fallback_enabled,
    resolve_geocode_fallback,
    sanitize_geocode_payload,
)
from contextlib import ExitStack
import tourism_query


# ---------------------------------------------------------------------------
# mapper
# ---------------------------------------------------------------------------

def _row(name_key, id_key, name, id_val):
    return {
        id_key: id_val,
        name_key: name,
        "DescriptionDetail": "景點說明",
        "Address": "台南市中西區",
        "Phone": "06-1234567",
        "OpenTime": "09:00-17:00",
        "City": "台南市",
        "Town": "中西區",
        "Position": {"PositionLat": 23.0, "PositionLon": 120.2},
        "Picture": {"PictureUrl1": "http://img1.jpg", "PictureDescription1": "封面"},
    }


class TestMapScenicSpot:
    def test_extracts_fields(self):
        payload = [_row("ScenicSpotName", "ScenicSpotID", "赤崁樓", "C001")]
        items = map_scenic_spot_payload(payload)
        assert items[0]["name"] == "赤崁樓"
        assert items[0]["item_id"] == "C001"
        assert items[0]["latitude"] == 23.0
        assert len(items[0]["pictures"]) == 1

    def test_skips_non_dict(self):
        items = map_scenic_spot_payload(["not_a_dict", _row("ScenicSpotName", "ScenicSpotID", "安平古堡", "C002")])
        assert len(items) == 1

    def test_empty(self):
        assert map_scenic_spot_payload([]) == []


class TestMapRestaurant:
    def test_extracts_fields(self):
        payload = [_row("RestaurantName", "RestaurantID", "度小月", "R001")]
        items = map_restaurant_payload(payload)
        assert items[0]["name"] == "度小月"
        assert items[0]["item_id"] == "R001"

    def test_empty(self):
        assert map_restaurant_payload([]) == []


class TestMapHotel:
    def test_extracts_fields(self):
        payload = [_row("HotelName", "HotelID", "台南大飯店", "H001")]
        items = map_hotel_payload(payload)
        assert items[0]["name"] == "台南大飯店"

    def test_empty(self):
        assert map_hotel_payload([]) == []


class TestMapActivity:
    def test_extracts_fields(self):
        payload = [_row("ActivityName", "ActivityID", "燈會", "A001")]
        items = map_activity_payload(payload)
        assert items[0]["name"] == "燈會"

    def test_empty(self):
        assert map_activity_payload([]) == []


# ---------------------------------------------------------------------------
# formatter
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_scenic_spot_no_filter(self):
        s = format_scenic_spot_summary("台南市", 5)
        assert "台南市" in s and "5" in s and "prechecked" in s

    def test_scenic_spot_with_keyword(self):
        s = format_scenic_spot_summary("台南市", 3, keyword="古蹟")
        assert "古蹟" in s and "filtered" in s

    def test_scenic_spot_with_landmark(self):
        s = format_scenic_spot_summary("高雄市", 2, landmark="駁二")
        assert "駁二" in s and "nearby" in s

    def test_restaurant_summary_no_keyword(self):
        s = format_restaurant_summary("台南市", 4)
        assert "台南市" in s and "prechecked" in s

    def test_restaurant_summary_with_keyword(self):
        s = format_restaurant_summary("台南市", 2, keyword="小吃")
        assert "小吃" in s and "filtered" in s

    def test_keyword_filtered(self):
        s = format_keyword_filtered_summary("高雄市", "碼頭", 6, "scenic_spot_city")
        assert "碼頭" in s and "6" in s

    def test_mapped_only(self):
        s = format_mapped_only_summary("hotel_city", "台南市", "mapped_only")
        assert "hotel_city" in s and "mapped_only" in s


# ---------------------------------------------------------------------------
# geocode_fallback
# ---------------------------------------------------------------------------

class TestGeocodeFallback:
    def test_disabled_by_default(self):
        result = resolve_geocode_fallback("台南車站", {})
        assert result["status"] == "disabled"

    def test_empty_query_skipped(self):
        result = resolve_geocode_fallback("", {})
        assert result["status"] == "skipped"

    def test_none_query_skipped(self):
        result = resolve_geocode_fallback(None, {})
        assert result["status"] == "skipped"

    def test_enabled_but_no_provider(self):
        config = {"geocode_fallback": {"enabled": True}}
        result = resolve_geocode_fallback("台南車站", config)
        assert result["status"] == "disabled"

    def test_sanitize_removes_extra_fields(self):
        payload = {"query": "台南", "latitude": 23.0, "longitude": 120.2, "secret": "hidden"}
        result = sanitize_geocode_payload(payload, {})
        assert "secret" not in result
        assert "latitude" in result

    def test_is_enabled_false_by_default(self):
        assert is_geocode_fallback_enabled({}) is False

    def test_is_enabled_true(self):
        assert is_geocode_fallback_enabled({"geocode_fallback": {"enabled": True}}) is True


# ---------------------------------------------------------------------------
# V2.1 Trail / CyclingRoute mappers
# ---------------------------------------------------------------------------

def _trail_node(trail_id="T001", name="太魯閣步道", length=2.3, height=150):
    pa = {"City": "花蓮縣", "Town": "秀林鄉", "StreetAddress": "花蓮縣秀林鄉"}
    return {
        "TrailID": trail_id,
        "TrailName": name,
        "Description": "步道說明",
        "PostalAddress": pa,
        "Telephones": [{"Tel": "03-8621100"}],
        "Images": [{"URL": "http://img.jpg", "Description": "步道"}],
        "TrailLength": length,
        "TrailHeight": height,
        "BestVisitMonths": "3-5月、9-11月",
        "IsCircle": 0,
        "VisitDuration": 120,
        "ServiceTimeInfo": "全天開放",
        "FeeInfo": "免費",
        "ParkingInfo": "停車場在入口",
    }


def _cycling_node(route_id="CR001", name="日月潭環湖自行車道", length=33.0):
    pa = {"City": "南投縣", "Town": "魚池鄉", "StreetAddress": "南投縣魚池鄉"}
    return {
        "CyclingRouteID": route_id,
        "CyclingRouteName": name,
        "Description": "自行車路線說明",
        "PostalAddress": pa,
        "Telephones": [],
        "Images": [{"URL": "http://bike.jpg", "Description": "路線"}],
        "TrailLength": length,
        "ServiceTimeInfo": "全天",
        "FeeInfo": "免費",
        "ParkingInfo": "日月潭遊客中心停車場",
    }


class TestMapTrailV21:
    def test_extracts_fields(self):
        data = {"value": [_trail_node()]}
        items = map_trail_payload_v21(data)
        assert len(items) == 1
        item = items[0]
        assert item["item_id"] == "T001"
        assert item["name"] == "太魯閣步道"
        assert item["trail_length_km"] == 2.3
        assert item["trail_height_m"] == 150
        assert item["best_visit_months"] == "3-5月、9-11月"
        assert item["is_circle"] == 0
        assert item["visit_duration_min"] == 120
        assert item["fee_info"] == "免費"
        assert item["city"] == "花蓮縣"

    def test_empty_value(self):
        assert map_trail_payload_v21({"value": []}) == []

    def test_list_input(self):
        items = map_trail_payload_v21([_trail_node("T002", "步道B", 1.0, 50)])
        assert items[0]["name"] == "步道B"


class TestMapCyclingRouteV21:
    def test_extracts_fields(self):
        data = {"value": [_cycling_node()]}
        items = map_cycling_route_payload_v21(data)
        assert len(items) == 1
        item = items[0]
        assert item["item_id"] == "CR001"
        assert item["name"] == "日月潭環湖自行車道"
        assert item["trail_length_km"] == 33.0
        assert item["fee_info"] == "免費"
        assert item["city"] == "南投縣"

    def test_empty_value(self):
        assert map_cycling_route_payload_v21({"value": []}) == []


# ---------------------------------------------------------------------------
# execute() helpers
# ---------------------------------------------------------------------------

def _city_ok(value="Tainan", label="台南市"):
    return {"needs_clarification": False, "normalized_value": value, "details": {"label": label, "reason": None}}

def _city_missing():
    return {"needs_clarification": True, "normalized_value": None, "details": {"label": None, "reason": "no_city_given"}}

def _endpoint_meta(state="prechecked"):
    return {"base_url": "https://tdx.transportdata.tw/api/basic", "path": "/v2/Tourism/ScenicSpot/{City}", "validation_state": state}

def _fake_response(data, url="https://tdx.example/tourism"):
    return SimpleNamespace(data=data, url=url)

def _apply_std_patches(stack: ExitStack, city_result=None) -> None:
    stack.enter_context(patch.object(tourism_query, "resolve_city", return_value=city_result or _city_ok()))
    stack.enter_context(patch.object(tourism_query, "get_endpoint", return_value=_endpoint_meta()))
    stack.enter_context(patch.object(tourism_query, "build_query_options", return_value={}))
    stack.enter_context(patch.object(tourism_query, "load_tourism_aliases", return_value=[]))
    stack.enter_context(patch.object(tourism_query, "resolve_geocode_fallback", return_value={"status": "disabled"}))
    # api_version: v10 確保舊測試繼續以 V1.0 JSON 路徑執行
    stack.enter_context(patch.object(tourism_query, "_load_runtime_config", return_value={"api_version": "v10"}))


# ---------------------------------------------------------------------------
# execute() tests
# ---------------------------------------------------------------------------

class TestExecuteInvalidIntent:
    def test_unknown_intent(self):
        result = tourism_query.execute({"intent": "no_such"})
        assert result["status"] == "invalid_input"
        assert result["unavailable_reason"] == "unsupported_intent"


class TestExecuteNeedsClarification:
    def test_no_city(self):
        with patch.object(tourism_query, "resolve_city", return_value=_city_missing()), \
             patch.object(tourism_query, "_load_runtime_config", return_value={}):
            result = tourism_query.execute({"intent": "scenic_spot_city"})
        assert result["status"] == "needs_clarification"

    def test_keyword_search_no_keyword(self):
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "tourism_keyword_search", "city": "台南市"})
        assert result["status"] == "needs_clarification"
        assert result["unavailable_reason"] == "keyword_required"

    def test_nearby_no_keyword_or_landmark(self):
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "station_nearby_tourism_summary", "city": "高雄市"})
        assert result["status"] == "needs_clarification"
        assert result["unavailable_reason"] == "keyword_or_landmark_required"


class TestExecuteMappedOnly:
    def test_hotel_city_mapped_only(self):
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "hotel_city", "city": "台南市"})
        assert result["status"] == "ok"
        assert "phase_2e" in result["unavailable_reason"]

    def test_activity_city_mapped_only(self):
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "activity_city", "city": "台南市"})
        assert result["status"] == "ok"
        assert result["items"] == []


class TestExecuteScenicSpot:
    def _fake_spots(self):
        return [
            {"ScenicSpotID": "S001", "ScenicSpotName": "赤崁樓", "DescriptionDetail": "古蹟", "Address": "台南市中西區",
             "Phone": "", "OpenTime": "08:30-17:30", "City": "台南市", "Town": "中西區", "ZipCode": "700",
             "WebsiteUrl": None, "Remarks": None, "Position": {"PositionLat": 23.0, "PositionLon": 120.2},
             "Picture": {}, "Class1": "歷史"},
            {"ScenicSpotID": "S002", "ScenicSpotName": "安平古堡", "DescriptionDetail": "砲台遺址", "Address": "台南市安平區",
             "Phone": "", "OpenTime": "08:30-17:30", "City": "台南市", "Town": "安平區", "ZipCode": "708",
             "WebsiteUrl": None, "Remarks": None, "Position": {}, "Picture": {}, "Class1": "歷史"},
        ]

    def test_returns_items(self):
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(self._fake_spots())
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "scenic_spot_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 2

    def test_keyword_filter(self):
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(self._fake_spots())
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "scenic_spot_city", "city": "台南市", "keyword": "赤崁"}, client=mock_client)
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "赤崁樓"


class TestExecuteRestaurant:
    def test_returns_items(self):
        fake_data = [
            {"RestaurantID": "R001", "RestaurantName": "度小月", "DescriptionDetail": "擔仔麵", "Address": "台南市中西區",
             "Phone": "", "OpenTime": "11:00-21:00", "City": "台南市", "Town": "中西區", "ZipCode": "700",
             "WebsiteUrl": None, "Remarks": None, "Position": {}, "Picture": {}, "Class": "小吃"},
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _fake_response(fake_data)
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "restaurant_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1


class TestExecuteErrors:
    def test_auth_error(self):
        from tdx_auth import TdxAuthError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxAuthError("401")
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "scenic_spot_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "auth_error"

    def test_upstream_error(self):
        from tdx_client import TdxClientError
        mock_client = MagicMock()
        mock_client.get.side_effect = TdxClientError("503")
        with ExitStack() as stack:
            _apply_std_patches(stack)
            result = tourism_query.execute({"intent": "scenic_spot_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "upstream_error"


# ---------------------------------------------------------------------------
# V2.1 JSON mapper tests（API server: tdx.transportdata.tw/api/tourism）
# ---------------------------------------------------------------------------

_ATTRACTION_JSON = {"value": [{"AttractionID": "A001", "AttractionName": "旗津海岸公園",
    "Description": "高雄著名景點",
    "PostalAddress": {"City": "高雄市", "Town": "旗津區", "ZipCode": "805", "StreetAddress": "旗津三路"},
    "Telephones": [{"Tel": "07-5551234"}],
    "Images": [{"URL": "http://ex.com/img.jpg", "Description": "海岸"}],
    "PositionLat": 22.616, "PositionLon": 120.270,
    "AttractionClasses": ["自然景觀"], "WebsiteUrl": None, "Remarks": None}]}

_RESTAURANT_JSON = {"value": [{"RestaurantID": "R001", "RestaurantName": "度小月",
    "Description": "擔仔麵老店",
    "PostalAddress": {"City": "台南市", "Town": "中西區", "ZipCode": "700", "StreetAddress": "中正路"},
    "Telephones": [{"Tel": "06-2231234"}], "Images": [],
    "PositionLat": 22.99, "PositionLon": 120.20,
    "CuisineClasses": [], "WebsiteUrl": None, "Remarks": None}]}

_HOTEL_JSON = {"value": [{"HotelID": "H001", "HotelName": "高雄漢來大飯店",
    "Description": "五星旅宿",
    "PostalAddress": {"City": "高雄市", "Town": "前金區", "ZipCode": "801", "StreetAddress": "成功一路"},
    "Telephones": [{"Tel": "07-2161766"}], "Images": [],
    "HotelStars": 5, "PositionLat": 22.63, "PositionLon": 120.30,
    "HotelClasses": [], "WebsiteUrl": None, "Remarks": None}]}

_EVENT_JSON = {"value": [{"EventID": "E001", "EventName": "台南燈節",
    "Description": "元宵燈節活動",
    "PostalAddress": {"City": "台南市", "Town": "中西區", "ZipCode": "700", "StreetAddress": "府前路"},
    "Telephones": [{"Tel": "06-2981234"}], "Images": [],
    "PositionLat": 23.00, "PositionLon": 120.20,
    "EventClasses": [], "StartDateTime": "2026-02-12", "EndDateTime": "2026-02-16",
    "WebsiteUrl": None, "Remarks": None}]}


class TestMapAttractionV21:
    def test_parses_fields(self):
        items = map_attraction_payload_v21(_ATTRACTION_JSON)
        assert len(items) == 1
        item = items[0]
        assert item["item_id"] == "A001"
        assert item["name"] == "旗津海岸公園"
        assert item["city"] == "高雄市"
        assert item["town"] == "旗津區"
        assert item["phone"] == "07-5551234"
        assert item["latitude"] == 22.616
        assert item["longitude"] == 120.270
        assert len(item["pictures"]) == 1
        assert item["pictures"][0]["url"] == "http://ex.com/img.jpg"

    def test_empty_value_list(self):
        items = map_attraction_payload_v21({"value": []})
        assert items == []

    def test_non_list_returns_empty(self):
        items = map_attraction_payload_v21(None)
        assert items == []


class TestMapRestaurantV21:
    def test_parses_fields(self):
        items = map_restaurant_payload_v21(_RESTAURANT_JSON)
        assert len(items) == 1
        assert items[0]["item_id"] == "R001"
        assert items[0]["name"] == "度小月"
        assert items[0]["city"] == "台南市"
        assert items[0]["phone"] == "06-2231234"


class TestMapHotelV21:
    def test_parses_fields(self):
        items = map_hotel_payload_v21(_HOTEL_JSON)
        assert len(items) == 1
        assert items[0]["item_id"] == "H001"
        assert items[0]["name"] == "高雄漢來大飯店"
        assert items[0]["hotel_stars"] == 5

    def test_hotel_stars_missing(self):
        data = {"value": [{"HotelID": "H002", "HotelName": "無星級", "PostalAddress": {},
                           "Telephones": [], "Images": [], "HotelClasses": [],
                           "WebsiteUrl": None, "Remarks": None}]}
        items = map_hotel_payload_v21(data)
        assert items[0]["hotel_stars"] is None


class TestMapEventV21:
    def test_parses_fields(self):
        items = map_event_payload_v21(_EVENT_JSON)
        assert len(items) == 1
        assert items[0]["item_id"] == "E001"
        assert items[0]["name"] == "台南燈節"
        assert items[0]["city"] == "台南市"
        assert items[0]["start_datetime"] == "2026-02-12"


# ---------------------------------------------------------------------------
# V2.1 execute() integration tests
# ---------------------------------------------------------------------------

def _v21_endpoint_meta():
    return {
        "base_url": "https://tdx.transportdata.tw/api/tourism/service/odata/V2",
        "path": "/Tourism/Attraction",
        "validation_state": "prechecked",
    }


def _apply_v21_patches(stack: ExitStack, city_result=None) -> None:
    stack.enter_context(patch.object(tourism_query, "resolve_city", return_value=city_result or _city_ok()))
    stack.enter_context(patch.object(tourism_query, "get_endpoint", return_value=_v21_endpoint_meta()))
    stack.enter_context(patch.object(tourism_query, "build_query_options", return_value={"$filter": "PostalAddress/City eq '台南市'", "$format": "JSON"}))
    stack.enter_context(patch.object(tourism_query, "load_tourism_aliases", return_value=[]))
    stack.enter_context(patch.object(tourism_query, "resolve_geocode_fallback", return_value={"status": "disabled"}))
    stack.enter_context(patch.object(tourism_query, "_load_runtime_config", return_value={"api_version": "v21"}))


class TestExecuteV21ScenicSpot:
    def test_returns_items_from_json(self):
        mock_client = MagicMock()
        mock_client.get.return_value = SimpleNamespace(data=_ATTRACTION_JSON, url="https://tdx.transportdata.tw/api/tourism/service/odata/V2/Tourism/Attraction")
        with ExitStack() as stack:
            _apply_v21_patches(stack)
            result = tourism_query.execute({"intent": "scenic_spot_city", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "ok"
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "旗津海岸公園"

    def test_accept_header_is_json_odata(self):
        mock_client = MagicMock()
        mock_client.get.return_value = SimpleNamespace(data=_ATTRACTION_JSON, url="https://tdx.transportdata.tw/api/tourism/service/odata/V2/Tourism/Attraction")
        with ExitStack() as stack:
            _apply_v21_patches(stack)
            tourism_query.execute({"intent": "scenic_spot_city", "city": "高雄市"}, client=mock_client)
        _, kwargs = mock_client.get.call_args
        assert kwargs.get("accept") == "application/json;odata.metadata=none"


class TestExecuteV21HotelAndEvent:
    def test_hotel_city_v21_returns_items(self):
        mock_client = MagicMock()
        mock_client.get.return_value = SimpleNamespace(data=_HOTEL_JSON, url="https://tdx.transportdata.tw/api/tourism/service/odata/V2/Tourism/Hotel")
        with ExitStack() as stack:
            _apply_v21_patches(stack)
            stack.enter_context(patch.object(tourism_query, "get_endpoint",
                return_value={"base_url": "https://tdx.transportdata.tw/api/tourism/service/odata/V2",
                              "path": "/Tourism/Hotel", "validation_state": "prechecked"}))
            result = tourism_query.execute({"intent": "hotel_city", "city": "高雄市"}, client=mock_client)
        assert result["status"] == "ok"
        assert result["items"][0]["name"] == "高雄漢來大飯店"

    def test_activity_city_v21_returns_items(self):
        mock_client = MagicMock()
        mock_client.get.return_value = SimpleNamespace(data=_EVENT_JSON, url="https://tdx.transportdata.tw/api/tourism/service/odata/V2/Tourism/Event")
        with ExitStack() as stack:
            _apply_v21_patches(stack)
            stack.enter_context(patch.object(tourism_query, "get_endpoint",
                return_value={"base_url": "https://tdx.transportdata.tw/api/tourism/service/odata/V2",
                              "path": "/Tourism/Event", "validation_state": "prechecked"}))
            result = tourism_query.execute({"intent": "activity_city", "city": "台南市"}, client=mock_client)
        assert result["status"] == "ok"
        assert result["items"][0]["name"] == "台南燈節"


class TestCityODataFilter:
    def test_v21_filter_format(self):
        """確認 V2.1 城市 $filter 字串格式正確（PostalAddress/City）。"""
        from query_option_builder import build_query_options
        opts = build_query_options(top=5, filter_expr="PostalAddress/City eq 'Kaohsiung'")
        assert opts["$filter"] == "PostalAddress/City eq 'Kaohsiung'"
        assert opts["$format"] == "JSON"
        assert opts["$top"] == "5"
