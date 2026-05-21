"""tdx-maas-route 測試。"""

from __future__ import annotations

import pytest

import tools.main as maas_main
from runtime.tdx.tdx_config import TDXConfig
from tools.main import execute


@pytest.fixture(autouse=True)
def _mock_path_planning(monkeypatch: pytest.MonkeyPatch) -> None:
    def _stub_execute(origin_resolved, destination_resolved, *, config, depart_time=None, preference="fastest"):
        del config, depart_time, preference
        return {
            "available": True,
            "routing_method": "path_planning_api",
            "summary": "已取得 1 條 MaaS live 路線方案。",
            "items": [
                {
                    "route_index": 1,
                    "routing_method": "path_planning_api",
                    "mode_primary": "rail",
                    "legs": [
                        {
                            "mode": "rail",
                            "from": origin_resolved.get("normalized_value"),
                            "to": destination_resolved.get("normalized_value"),
                            "label": "TDX MaaS live route",
                            "estimated_minutes": 35,
                            "note": "TDX MaaS live route",
                        }
                    ],
                    "transfer_count": 0,
                    "total_estimated_minutes": 35,
                    "note": "TDX MaaS live route",
                }
            ],
        }

    monkeypatch.setattr(maas_main._strategy_a, "execute", _stub_execute)
    monkeypatch.setattr(
        maas_main._strategy_a,
        "resolve_coordinates",
        lambda resolved, *, config: {"lat": 22.687391, "lng": 120.307487} if resolved.get("normalized_value") == "左營" else {"lat": 22.9999, "lng": 120.2270},
    )


class TestP2_01_ZuoyingToTainan:
    def test_ok_status(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南", "preference": "fastest"},
            config=config,
        )
        assert result["status"] == "ok"
        assert result["skill"] == "tdx-maas-route"

    def test_items_le_3(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南", "preference": "fastest"},
            config=config,
        )
        assert len(result["items"]) <= 3
        assert result["returned_count"] <= 3

    def test_routing_method_present(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南", "preference": "fastest"},
            config=config,
        )
        assert result["routing_method"] in (
            "path_planning_api",
            "self_assembled",
            "suggestion_only",
        )

    def test_normalized_query_origin(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南", "preference": "fastest"},
            config=config,
        )
        nq = result["normalized_query"]
        assert nq["origin"]["raw"] == "左營"
        assert nq["destination"]["raw"] == "台南"
        assert nq["preference"] == "fastest"
        assert nq["origin"]["coordinates"]["lat"] == 22.687391


class TestP2_02_KaohsiungToXiaogang:
    def test_preference_min_transfer(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "高雄", "destination": "小港", "preference": "min_transfer"},
            config=config,
        )
        assert result["status"] == "ok"
        nq = result["normalized_query"]
        assert nq["preference"] == "min_transfer"


class TestP2_03_BanqiaoToTaipei:
    def test_depart_time_parsed(self, config: TDXConfig) -> None:
        result = execute(
            {
                "origin": "板橋",
                "destination": "台北",
                "depart_time": "明天 19:00",
            },
            config=config,
        )
        assert result["status"] == "ok"
        dt = result["normalized_query"]["depart_time"]
        assert dt["timezone"] == "Asia/Taipei"
        assert dt.get("normalized_iso8601") is not None


class TestP2_04_MissingOrigin:
    def test_missing_origin(self, config: TDXConfig) -> None:
        result = execute({"destination": "左營"}, config=config)
        assert result["status"] == "invalid_input"
        assert result["needs_clarification"] is True

    def test_missing_destination(self, config: TDXConfig) -> None:
        result = execute({"origin": "台北"}, config=config)
        assert result["status"] == "invalid_input"
        assert result["needs_clarification"] is True


class TestP2_05_AmbiguousDestination:
    def test_ambiguous_destination(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "台中", "destination": "醫院"},
            config=config,
        )
        assert result["status"] == "ambiguous"
        assert result["needs_clarification"] is True


class TestP2_06_RoutingMethodReflectsStrategy:
    def test_routing_method_is_path_planning(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南"},
            config=config,
        )
        assert result["routing_method"] == "path_planning_api"

    def test_each_item_has_routing_method(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南"},
            config=config,
        )
        for item in result["items"]:
            assert "routing_method" in item


class TestP2_07_FallbackChain:
    def test_fallback_not_used_when_path_planning_available(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南"},
            config=config,
        )
        assert result["fallback_used"] is False
        assert result["fallback_reason"] is None


class TestOutputSchema:
    def test_all_required_fields(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南"},
            config=config,
        )
        required_fields = [
            "skill", "sub_command", "status", "needs_clarification",
            "clarification_question", "routing_method", "summary",
            "normalized_query", "items", "returned_count",
            "total_candidate_count", "truncated", "truncation_note",
            "fallback_used", "fallback_reason", "source", "errors",
        ]
        for field in required_fields:
            assert field in result, f"缺少必要欄位: {field}"

    def test_source_provider(self, config: TDXConfig) -> None:
        result = execute(
            {"origin": "左營", "destination": "台南"},
            config=config,
        )
        assert result["source"]["provider"] == "TDX"

    def test_error_status_schema(self, config: TDXConfig) -> None:
        result = execute(
            {"destination": "台南"},
            config=config,
        )
        assert "routing_method" in result
        assert "errors" in result
        assert result["status"] == "invalid_input"
