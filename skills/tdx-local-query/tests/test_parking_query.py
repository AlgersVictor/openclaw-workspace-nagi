"""parking_query 測試。

Case P1-PARK-01 ~ P1-PARK-02。
B1 修正後：parking v1 端點可用，改以 mock live client 測試正常流程。
"""

from __future__ import annotations

import pytest

import tools.parking_query as parking_query_module
from runtime.tdx.tdx_config import TDXConfig
from runtime.tdx.tdx_entity_resolver import TDXEntityResolver
from tools.parking_query import execute

_DUMMY_PARKING_ROW = {
    "ParkingAvailableID": "TP-001",
    "ParkingName": {"Zh_tw": "信義停車場"},
    "TotalSpaces": 200,
    "AvailableSpaces": 45,
    "ChargeFree": False,
    "Address": {"Zh_tw": "台北市信義區忠孝東路五段"},
    "UpdateTime": "2026-05-19T09:30:00+08:00",
}


@pytest.fixture(autouse=True)
def _mock_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        def get(self, endpoint_key, path_params=None, query_params=None):
            assert endpoint_key == "parking.availability"
            return [_DUMMY_PARKING_ROW]

    monkeypatch.setattr(parking_query_module, "_build_live_client", lambda config: DummyClient())


class TestP1PARK01_NormalQuery:
    """台北停車場查詢（v1 live API）。"""

    def test_ok_status(self, config: TDXConfig) -> None:
        result = execute(
            {"city": "台北", "keyword": "信義"},
            config=config,
            resolver=TDXEntityResolver(config),
        )
        assert result["status"] == "ok"
        assert result["fallback_used"] is False

    def test_items_present(self, config: TDXConfig) -> None:
        result = execute(
            {"city": "台北", "keyword": "信義"},
            config=config,
            resolver=TDXEntityResolver(config),
        )
        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["name"] == "信義停車場"
        assert item["available_spaces"] == 45

    def test_keyword_filter(self, config: TDXConfig) -> None:
        result = execute(
            {"city": "台北", "keyword": "大安"},
            config=config,
            resolver=TDXEntityResolver(config),
        )
        assert result["status"] == "no_data"
        assert len(result["items"]) == 0

    def test_normalized_query(self, config: TDXConfig) -> None:
        result = execute(
            {"city": "台北"},
            config=config,
            resolver=TDXEntityResolver(config),
        )
        nq = result["normalized_query"]
        assert nq["city"]["normalized_value"] == "Taipei"


class TestP1PARK02_MissingCity:
    """缺少 city → invalid_input。"""

    def test_invalid_without_city(self, config: TDXConfig) -> None:
        result = execute(
            {"keyword": "信義區"},
            config=config,
            resolver=TDXEntityResolver(config),
        )
        assert result["status"] == "invalid_input"
        assert result["needs_clarification"] is True

    def test_output_schema(self, config: TDXConfig) -> None:
        result = execute(
            {"keyword": "信義區"},
            config=config,
            resolver=TDXEntityResolver(config),
        )
        required_fields = [
            "skill", "sub_command", "status", "needs_clarification",
            "clarification_question", "items", "returned_count",
            "source", "errors",
        ]
        for field in required_fields:
            assert field in result, f"缺少必要欄位: {field}"
