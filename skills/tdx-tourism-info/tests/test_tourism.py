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
    stack.enter_context(patch.object(tourism_query, "_load_runtime_config", return_value={}))


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
