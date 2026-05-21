"""tdx-shared-core unit tests。"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED_CORE = Path(__file__).resolve().parents[1]
if str(_SHARED_CORE) not in sys.path:
    sys.path.insert(0, str(_SHARED_CORE))

import pytest

from endpoint_registry import get_endpoint
from query_option_builder import build_query_options
from resolver_city import resolve_city
from resolver_rail_system import resolve_rail_system
from resolver_station_alias import resolve_station_alias
from resolver_coordinate_input import validate_coordinate_input
from resolver_route_preferences import normalize_route_preferences
from resolver_transit_modes import normalize_transit_modes


# ---------------------------------------------------------------------------
# endpoint_registry
# ---------------------------------------------------------------------------

class TestGetEndpoint:
    def test_known_key_returns_meta(self):
        ep = get_endpoint("metro_station")
        assert "base_url" in ep
        assert "path" in ep
        assert "validation_state" in ep

    def test_unknown_key_raises(self):
        with pytest.raises(KeyError):
            get_endpoint("no_such_endpoint_xyz")

    def test_path_contains_placeholder(self):
        ep = get_endpoint("metro_station")
        assert "{" in ep["path"]


# ---------------------------------------------------------------------------
# query_option_builder
# ---------------------------------------------------------------------------

class TestBuildQueryOptions:
    def test_defaults(self):
        result = build_query_options(top=5)
        assert str(result["$top"]) == "5"

    def test_fmt_default_json(self):
        result = build_query_options(top=1)
        assert result.get("$format") == "JSON"

    def test_custom_fmt(self):
        result = build_query_options(top=1, fmt="XML")
        assert result["$format"] == "XML"

    def test_filter_expr_included(self):
        result = build_query_options(top=10, filter_expr="City eq 'Taipei'")
        assert result["$filter"] == "City eq 'Taipei'"

    def test_select_included(self):
        result = build_query_options(top=5, select="StationID,StationName")
        assert result["$select"] == "StationID,StationName"

    def test_top_zero_raises(self):
        with pytest.raises(ValueError):
            build_query_options(top=0)

    def test_top_negative_raises(self):
        with pytest.raises(ValueError):
            build_query_options(top=-1)

    def test_no_extra_keys_when_none(self):
        result = build_query_options(top=3)
        assert "$filter" not in result
        assert "$select" not in result


# ---------------------------------------------------------------------------
# resolver_city
# ---------------------------------------------------------------------------

class TestResolveCity:
    def test_empty_needs_clarification(self):
        r = resolve_city("")
        assert r["needs_clarification"] is True
        assert r["details"]["reason"] == "missing_city"

    def test_none_needs_clarification(self):
        r = resolve_city(None)
        assert r["needs_clarification"] is True

    def test_taipei_aliases(self):
        for alias in ("台北", "臺北", "台北市", "臺北市"):
            r = resolve_city(alias)
            assert r["status"] == "ok", f"failed: {alias}"
            assert r["normalized_value"] == "Taipei"
            assert r["needs_clarification"] is False

    def test_tainan_alias(self):
        r = resolve_city("台南")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "Tainan"

    def test_kaohsiung_alias(self):
        r = resolve_city("高雄市")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "Kaohsiung"

    def test_taichung_alias(self):
        r = resolve_city("臺中")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "Taichung"

    def test_unknown_needs_clarification(self):
        r = resolve_city("外星市")
        assert r["needs_clarification"] is True

    def test_ok_has_label(self):
        r = resolve_city("台北")
        assert r["details"]["label"] is not None

    # 鄉鎮市區落點查詢
    def test_district_full_name_resolves(self):
        cases = [
            ("潮州鎮", "PingtungCounty"),
            ("羅東鎮", "YilanCounty"),
            ("板橋區", "NewTaipei"),
            ("埔里鎮", "NantouCounty"),
            ("鹿港鎮", "ChanghuaCounty"),
            ("臺東市", "TaitungCounty"),
            ("台東市", "TaitungCounty"),
            ("花蓮市", "HualienCounty"),
            ("馬公市", "PenghuCounty"),
            ("金城鎮", "KinmenCounty"),
            ("南竿鄉", "LienchiangCounty"),
            ("竹北市", "HsinchuCounty"),
            ("斗六市", "YunlinCounty"),
            ("太保市", "ChiayiCounty"),
            ("竹崎鄉", "ChiayiCounty"),
            ("三地門鄉", "PingtungCounty"),
            ("那瑪夏區", "Kaohsiung"),
            ("台西鄉", "YunlinCounty"),
            ("臺西鄉", "YunlinCounty"),
        ]
        for name, expected_city in cases:
            r = resolve_city(name)
            assert r["status"] == "ok", f"failed: {name} → {r}"
            assert r["normalized_value"] == expected_city, f"{name}: got {r['normalized_value']}"
            assert r["details"].get("matched_by") == "district"
            assert r["needs_clarification"] is False

    def test_district_short_alias_resolves(self):
        cases = [
            ("潮州", "PingtungCounty"),
            ("羅東", "YilanCounty"),
            ("鹿港", "ChanghuaCounty"),
            ("埔里", "NantouCounty"),
            ("竹北", "HsinchuCounty"),
            ("阿里山", "ChiayiCounty"),
            ("東引", "LienchiangCounty"),
            ("馬公", "PenghuCounty"),
            ("恆春", "PingtungCounty"),
            ("斗六", "YunlinCounty"),
            ("虎尾", "YunlinCounty"),
            ("豐原", "Taichung"),
            ("岡山", "Kaohsiung"),
            ("礁溪", "YilanCounty"),
        ]
        for name, expected_city in cases:
            r = resolve_city(name)
            assert r["status"] == "ok", f"failed: {name} → {r}"
            assert r["normalized_value"] == expected_city, f"{name}: got {r['normalized_value']}"

    def test_ambiguous_district_needs_clarification(self):
        ambiguous = ["大安區", "東區", "南區", "北區", "西區", "中正區", "信義區", "中山區"]
        for name in ambiguous:
            r = resolve_city(name)
            assert r["needs_clarification"] is True, f"{name} should be ambiguous"
            assert r["details"]["reason"] == "ambiguous_district"
            assert len(r["candidates"]) >= 2, f"{name}: expected candidates"

    def test_ambiguous_district_candidates_content(self):
        r = resolve_city("大安區")
        assert "臺北市" in r["candidates"]
        assert "臺中市" in r["candidates"]

        r = resolve_city("東區")
        assert len(r["candidates"]) == 4

        r = resolve_city("中正區")
        assert "臺北市" in r["candidates"]
        assert "基隆市" in r["candidates"]

    def test_city_aliases_still_take_priority(self):
        # CITY_ALIASES 應優先於 DISTRICT_TO_CITY
        r = resolve_city("台北")
        assert r["normalized_value"] == "Taipei"
        assert r["details"].get("matched_by") != "district"

        r = resolve_city("屏東")
        assert r["normalized_value"] == "PingtungCounty"
        assert r["details"].get("matched_by") != "district"


# ---------------------------------------------------------------------------
# resolver_rail_system
# ---------------------------------------------------------------------------

class TestResolveRailSystem:
    def test_empty_needs_clarification(self):
        r = resolve_rail_system("")
        assert r["needs_clarification"] is True

    def test_trtc_aliases(self):
        for alias in ("台北捷運", "臺北捷運", "北捷"):
            r = resolve_rail_system(alias)
            assert r["status"] == "ok", f"failed: {alias}"
            assert r["normalized_value"] == "TRTC"

    def test_krtc_aliases(self):
        for alias in ("高雄捷運", "高捷"):
            r = resolve_rail_system(alias)
            assert r["status"] == "ok"
            assert r["normalized_value"] == "KRTC"

    def test_klrt_aliases(self):
        for alias in ("高雄輕軌", "輕軌"):
            r = resolve_rail_system(alias)
            assert r["status"] == "ok"
            assert r["normalized_value"] == "KLRT"

    def test_unknown_needs_clarification(self):
        r = resolve_rail_system("外星捷運")
        assert r["needs_clarification"] is True


# ---------------------------------------------------------------------------
# resolver_station_alias
# ---------------------------------------------------------------------------

class TestResolveStationAlias:
    def test_empty_missing_station(self):
        r = resolve_station_alias("")
        assert r["needs_clarification"] is True
        assert r["details"]["reason"] == "missing_station"

    def test_none_missing_station(self):
        r = resolve_station_alias(None)
        assert r["needs_clarification"] is True

    def test_known_station_trtc(self):
        r = resolve_station_alias("北車", "TRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "台北車站"

    def test_known_station_krtc(self):
        r = resolve_station_alias("美麗島", "KRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "美麗島"

    def test_ambiguous_returns_candidates(self):
        r = resolve_station_alias("左營")
        assert r["needs_clarification"] is True
        assert len(r["candidates"]) > 0

    def test_unknown_station(self):
        r = resolve_station_alias("不存在站", "TRTC")
        assert r["needs_clarification"] is True

    def test_klrt_station_missing_name(self):
        # 美麗島 in KLRT has station_name=None → should not return ok
        r = resolve_station_alias("美麗島", "KLRT")
        assert r["status"] != "ok"

    def test_trtc_transfer_station(self):
        r = resolve_station_alias("忠孝復興", "TRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "忠孝復興"
        assert "BL15" in r["details"]["station_id"]
        assert "BR10" in r["details"]["station_id"]

    def test_trtc_single_line_station(self):
        r = resolve_station_alias("淡水", "TRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "淡水"
        assert r["details"]["station_id"] == "R28"

    def test_trtc_short_alias(self):
        r = resolve_station_alias("小巨蛋", "TRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "台北小巨蛋"

    def test_trtc_ambiguous_daan(self):
        r = resolve_station_alias("大安")
        assert r["needs_clarification"] is True
        assert len(r["candidates"]) >= 2

    def test_krtc_single_station(self):
        r = resolve_station_alias("高雄車站", "KRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "高雄車站"
        assert r["details"]["station_id"] == "R11"

    def test_krtc_left_station_no_suffix(self):
        r = resolve_station_alias("左營", "KRTC")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "左營"
        assert r["details"]["station_id"] == "R16"


# ---------------------------------------------------------------------------
# resolver_coordinate_input
# ---------------------------------------------------------------------------

class TestValidateCoordinateInput:
    def test_none_needs_clarification(self):
        r = validate_coordinate_input(None)
        assert r["needs_clarification"] is True

    def test_empty_string(self):
        r = validate_coordinate_input("")
        assert r["needs_clarification"] is True

    def test_valid_string(self):
        r = validate_coordinate_input("25.0478, 121.5318")
        assert r["status"] == "ok"
        assert r["details"]["lat"] == pytest.approx(25.0478)
        assert r["details"]["lng"] == pytest.approx(121.5318)

    def test_normalized_value_6dp(self):
        r = validate_coordinate_input("23.0, 120.2")
        assert r["normalized_value"] == "23.000000,120.200000"

    def test_bad_string_format(self):
        r = validate_coordinate_input("25.04")
        assert r["status"] == "needs_clarification"

    def test_non_numeric_string(self):
        r = validate_coordinate_input("abc,def")
        assert r["status"] == "needs_clarification"

    def test_valid_dict(self):
        r = validate_coordinate_input({"lat": 22.9, "lng": 120.1})
        assert r["status"] == "ok"

    def test_dict_missing_key(self):
        r = validate_coordinate_input({"lat": 22.9})
        assert r["status"] == "invalid_input"

    def test_dict_non_numeric(self):
        r = validate_coordinate_input({"lat": "x", "lng": "y"})
        assert r["status"] == "invalid_input"

    def test_lat_out_of_range(self):
        r = validate_coordinate_input("91.0, 120.0")
        assert r["status"] == "invalid_input"
        assert r["details"]["reason"] == "latitude_out_of_range"

    def test_lng_out_of_range(self):
        r = validate_coordinate_input("25.0, 181.0")
        assert r["status"] == "invalid_input"
        assert r["details"]["reason"] == "longitude_out_of_range"

    def test_unsupported_type(self):
        r = validate_coordinate_input(12345)
        assert r["status"] == "invalid_input"
        assert r["details"]["reason"] == "unsupported_coordinate_type"


# ---------------------------------------------------------------------------
# resolver_route_preferences
# ---------------------------------------------------------------------------

class TestNormalizeRoutePreferences:
    def test_defaults(self):
        r = normalize_route_preferences({})
        assert r["status"] == "ok"
        assert r["normalized_value"]["top"] == "1"
        assert r["normalized_value"]["gc"] == "0.0"

    def test_top_valid(self):
        r = normalize_route_preferences({"top": 3})
        assert r["normalized_value"]["top"] == "3"

    def test_top_zero_invalid(self):
        r = normalize_route_preferences({"top": 0})
        assert r["status"] == "invalid_input"
        assert r["details"]["reason"] == "invalid_top"

    def test_top_negative_invalid(self):
        r = normalize_route_preferences({"top": -1})
        assert r["status"] == "invalid_input"

    def test_depart_and_arrival_conflict(self):
        r = normalize_route_preferences({"depart": "09:00", "arrival": "10:00"})
        assert r["status"] == "invalid_input"
        assert r["details"]["reason"] == "depart_and_arrival_conflict"

    def test_depart_only(self):
        r = normalize_route_preferences({"depart": "09:00"})
        assert r["status"] == "ok"
        assert "depart" in r["normalized_value"]
        assert "arrival" not in r["normalized_value"]

    def test_transfer_time_valid(self):
        r = normalize_route_preferences({"transfer_time": 5})
        assert r["normalized_value"]["transfer_time"] == "5"

    def test_transfer_time_negative_invalid(self):
        r = normalize_route_preferences({"transfer_time": -1})
        assert r["status"] == "invalid_input"
        assert r["details"]["reason"] == "invalid_transfer_time"

    def test_first_last_mile_modes(self):
        r = normalize_route_preferences({"first_mile_mode": "walk", "last_mile_mode": "bike"})
        assert r["normalized_value"]["first_mile_mode"] == "walk"
        assert r["normalized_value"]["last_mile_mode"] == "bike"


# ---------------------------------------------------------------------------
# resolver_transit_modes
# ---------------------------------------------------------------------------

class TestNormalizeTransitModes:
    def test_none_returns_default(self):
        r = normalize_transit_modes(None)
        assert r["status"] == "ok"
        assert r["details"]["used_default"] is True
        assert "3" in r["normalized_value"]

    def test_empty_string_returns_default(self):
        r = normalize_transit_modes("")
        assert r["status"] == "ok"
        assert r["details"]["used_default"] is True

    def test_alias_hsr(self):
        r = normalize_transit_modes("hsr")
        assert r["status"] == "ok"
        assert r["normalized_value"] == "3"

    def test_alias_metro(self):
        r = normalize_transit_modes("mrt")
        assert r["normalized_value"] == "6"

    def test_numeric_string(self):
        r = normalize_transit_modes("5,6")
        assert r["status"] == "ok"
        assert "5" in r["normalized_value"]
        assert "6" in r["normalized_value"]

    def test_list_input(self):
        r = normalize_transit_modes(["hsr", "metro"])
        assert r["status"] == "ok"
        assert "3" in r["normalized_value"]
        assert "6" in r["normalized_value"]

    def test_no_duplicates(self):
        r = normalize_transit_modes("mrt,metro")
        assert r["normalized_value"].count("6") == 1

    def test_unknown_mode(self):
        r = normalize_transit_modes("teleport")
        assert r["status"] == "invalid_input"
        assert "teleport" in r["details"]["unknown_modes"]

    def test_unsupported_type(self):
        r = normalize_transit_modes(123)
        assert r["status"] == "invalid_input"

    def test_empty_list_needs_clarification(self):
        r = normalize_transit_modes([])
        assert r["needs_clarification"] is True
