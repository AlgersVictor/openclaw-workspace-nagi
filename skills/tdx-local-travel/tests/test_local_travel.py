"""tdx-local-travel unit tests。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_WORKSPACE_NAGI = _SKILL_ROOT.parents[1]  # workspace-nagi/

for _p in [str(_SKILL_ROOT), str(_WORKSPACE_NAGI)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import pure helpers at module level — no TdxClient deps, safe across reloads.
from tools.main import _resolve_city, _build_spot_summary


# ---------------------------------------------------------------------------
# _resolve_city — 回傳 city_label（如「高雄市」）
# ---------------------------------------------------------------------------

class TestResolveCity:
    def test_direct_alias(self):
        assert _resolve_city("台中", None) == "臺中市"
        assert _resolve_city("臺南", None) == "臺南市"
        assert _resolve_city("高雄", None) == "高雄市"

    def test_with_suffix(self):
        # 帶「市」後綴直接查到
        assert _resolve_city("高雄市", None) == "高雄市"
        assert _resolve_city("台北市", None) == "臺北市"
        assert _resolve_city("臺北市", None) == "臺北市"

    def test_unknown_city_returns_none(self):
        assert _resolve_city("外星市", None) is None

    def test_empty_city_uses_destination_poi(self):
        # 駁二 → 高雄市 (via POI_CITY_MAP + resolver)
        result = _resolve_city("", "駁二藝術特區")
        assert result == "高雄市"

    def test_empty_city_and_destination_returns_none(self):
        assert _resolve_city("", None) is None

    def test_unknown_destination_returns_none(self):
        assert _resolve_city("", "外星景點XYZ") is None

    # 原本不支援的縣市
    def test_pingtung_county(self):
        assert _resolve_city("屏東", None) == "屏東縣"
        assert _resolve_city("屏東縣", None) == "屏東縣"

    def test_hualien_county(self):
        assert _resolve_city("花蓮", None) == "花蓮縣"

    def test_yilan_county(self):
        assert _resolve_city("宜蘭", None) == "宜蘭縣"

    def test_taitung_county(self):
        assert _resolve_city("台東", None) == "臺東縣"
        assert _resolve_city("臺東", None) == "臺東縣"

    def test_penghu_county(self):
        assert _resolve_city("澎湖", None) == "澎湖縣"

    def test_kinmen_county(self):
        assert _resolve_city("金門", None) == "金門縣"

    def test_lienchiang_county(self):
        assert _resolve_city("連江", None) == "連江縣"
        assert _resolve_city("馬祖", None) == "連江縣"

    def test_nantou_county(self):
        assert _resolve_city("南投", None) == "南投縣"

    def test_changhua_county(self):
        assert _resolve_city("彰化", None) == "彰化縣"

    def test_miaoli_county(self):
        assert _resolve_city("苗栗", None) == "苗栗縣"

    def test_yunlin_county(self):
        assert _resolve_city("雲林", None) == "雲林縣"

    # 鄉鎮區查詢
    def test_district_hengchun(self):
        # 恆春 → 屏東縣（DISTRICT_TO_CITY 短名別名）
        assert _resolve_city("恆春", None) == "屏東縣"

    def test_district_jiaosi(self):
        # 礁溪 → 宜蘭縣
        assert _resolve_city("礁溪", None) == "宜蘭縣"

    def test_district_luodong(self):
        # 羅東 → 宜蘭縣
        assert _resolve_city("羅東", None) == "宜蘭縣"

    def test_district_puli(self):
        # 埔里 → 南投縣
        assert _resolve_city("埔里", None) == "南投縣"

    def test_district_kenting(self):
        # 南灣（墾丁一帶）→ 屏東縣
        assert _resolve_city("南灣", None) == "屏東縣"

    def test_district_green_island(self):
        # 綠島 → 臺東縣
        assert _resolve_city("綠島", None) == "臺東縣"

    def test_district_lanyu(self):
        # 蘭嶼 → 臺東縣
        assert _resolve_city("蘭嶼", None) == "臺東縣"

    def test_district_alishan(self):
        # 阿里山 → 嘉義縣
        assert _resolve_city("阿里山", None) == "嘉義縣"

    def test_keelung_city(self):
        assert _resolve_city("基隆", None) == "基隆市"

    def test_hsinchu_county_vs_city(self):
        # 「新竹」預設對應新竹縣（CITY_ALIASES 定義）
        assert _resolve_city("新竹", None) == "新竹縣"
        # 「新竹市」明確對應新竹市
        assert _resolve_city("新竹市", None) == "新竹市"

    def test_chiayi_county_vs_city(self):
        # 「嘉義」預設對應嘉義縣
        assert _resolve_city("嘉義", None) == "嘉義縣"
        # 「嘉義市」明確對應嘉義市
        assert _resolve_city("嘉義市", None) == "嘉義市"


# ---------------------------------------------------------------------------
# _build_spot_summary
# ---------------------------------------------------------------------------

def _make_items(n: int) -> list[dict]:
    return [{"name": f"景點{i}", "address": f"地址{i}", "open_time": "09:00", "description": f"說明{i}"} for i in range(n)]


class TestBuildSpotSummary:
    def test_max_5_items(self):
        items = _make_items(10)
        result = _build_spot_summary(items, None)
        assert len(result) == 5

    def test_fewer_than_5(self):
        items = _make_items(3)
        result = _build_spot_summary(items, None)
        assert len(result) == 3

    def test_destination_inserted_when_missing(self):
        items = _make_items(2)
        result = _build_spot_summary(items, "特定景點")
        assert result[0]["name"] == "特定景點"
        assert result[0]["description"] == "使用者指定景點。"

    def test_destination_not_duplicated_when_present(self):
        items = [{"name": "景點A", "address": "", "open_time": "", "description": ""}]
        result = _build_spot_summary(items, "景點A")
        assert len([r for r in result if r["name"] == "景點A"]) == 1

    def test_description_truncated_to_80(self):
        long_desc = "A" * 200
        items = [{"name": "景點", "address": "", "open_time": "", "description": long_desc}]
        result = _build_spot_summary(items, None)
        assert len(result[0]["description"]) <= 83  # 80 + "…"


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------

class TestExecute:
    def _run(self, params, spot_items=None):
        """Import fresh after conftest reloads tools.*, mock _query_tourism."""
        import tools.main as m
        with patch.object(m, "_query_tourism", return_value=spot_items or []):
            return m.execute(params)

    def test_no_city_no_destination(self):
        result = self._run({})
        assert result["status"] == "invalid_input"
        assert result["needs_clarification"] is True

    def test_unknown_city(self):
        result = self._run({"city": "外星市"})
        assert result["status"] == "ambiguous"
        assert result["needs_clarification"] is True

    def test_ok_with_city(self):
        spots = [{"name": "駁二", "address": "高雄市鹽埕區", "open_time": "10:00-22:00", "description": "藝術特區"}]
        result = self._run({"city": "高雄"}, spot_items=spots)
        assert result["status"] == "ok"
        item_types = {i["item_type"] for i in result["items"]}
        assert "spots" in item_types
        assert "transport_plan" in item_types

    def test_ok_no_spots_still_has_transport(self):
        result = self._run({"city": "台南"}, spot_items=[])
        assert result["status"] == "ok"
        item_types = [i["item_type"] for i in result["items"]]
        assert "transport_plan" in item_types

    def test_origin_adds_from_origin_plan(self):
        result = self._run({"city": "高雄", "origin": "台北", "destination": "美麗島"})
        plan_types = [i.get("plan_type") for i in result["items"] if i["item_type"] == "transport_plan"]
        assert "from_origin" in plan_types

    def test_normalized_query_populated(self):
        result = self._run({"city": "台中", "destination": "宮原眼科", "travel_theme": "美食"})
        nq = result["normalized_query"]
        assert nq["city"] == "臺中市"
        assert nq["destination"] == "宮原眼科"

    def test_destination_via_poi_map(self):
        result = self._run({"destination": "赤崁樓"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "臺南市"

    # 全縣市執行測試（無景點，只確認不回 ambiguous）
    def test_pingtung_ok(self):
        result = self._run({"city": "屏東"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "屏東縣"

    def test_hualien_ok(self):
        result = self._run({"city": "花蓮"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "花蓮縣"

    def test_yilan_ok(self):
        result = self._run({"city": "宜蘭"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "宜蘭縣"

    def test_taitung_ok(self):
        result = self._run({"city": "台東"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "臺東縣"

    def test_kinmen_ok(self):
        result = self._run({"city": "金門"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "金門縣"

    def test_penghu_ok(self):
        result = self._run({"city": "澎湖"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "澎湖縣"

    def test_matsu_ok(self):
        result = self._run({"city": "馬祖"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "連江縣"

    def test_hengchun_district_ok(self):
        # 恆春（鄉鎮名）→ 屏東縣
        result = self._run({"city": "恆春"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "屏東縣"

    def test_alishan_district_ok(self):
        result = self._run({"city": "阿里山"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "嘉義縣"
