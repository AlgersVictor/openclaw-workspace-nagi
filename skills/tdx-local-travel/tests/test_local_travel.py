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
# _resolve_city
# ---------------------------------------------------------------------------

class TestResolveCity:
    def test_direct_alias(self):
        assert _resolve_city("台中", None) == "台中"
        assert _resolve_city("臺南", None) == "台南"
        assert _resolve_city("高雄", None) == "高雄"

    def test_partial_match(self):
        assert _resolve_city("高雄市", None) == "高雄"
        assert _resolve_city("台北市", None) == "台北"

    def test_unknown_city_returns_none(self):
        assert _resolve_city("外星市", None) is None

    def test_empty_city_uses_destination_poi(self):
        # 駁二 → 高雄 (from POI_CITY_MAP)
        result = _resolve_city("", "駁二藝術特區")
        assert result == "高雄"

    def test_empty_city_and_destination_returns_none(self):
        assert _resolve_city("", None) is None

    def test_unknown_destination_returns_none(self):
        assert _resolve_city("", "外星景點XYZ") is None


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
        assert nq["city"] == "台中"
        assert nq["destination"] == "宮原眼科"

    def test_destination_via_poi_map(self):
        result = self._run({"destination": "赤崁樓"})
        assert result["status"] == "ok"
        assert result["normalized_query"]["city"] == "台南"
