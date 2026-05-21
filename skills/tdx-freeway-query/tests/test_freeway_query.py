"""tdx-freeway-query unit tests — mock TDX API。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.freeway_query import _normalize_ic, _km_float, _resolve_km_range

# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------

class TestNormalizeIC:
    def test_strip_suffix(self):
        assert _normalize_ic("中正交流道") == "中正"
        assert _normalize_ic("岡山交流道") == "岡山"
        assert _normalize_ic("鼎金系統交流道") == "鼎金"
        assert _normalize_ic("仁德服務區") == "仁德"
        assert _normalize_ic("岡山") == "岡山"  # 無後綴不變

    def test_strip_system(self):
        assert _normalize_ic("鼎金系統") == "鼎金"


class TestKmFloat:
    def test_normal(self):
        assert _km_float("358K+500") == pytest.approx(358.5)
        assert _km_float("346K+000") == pytest.approx(346.0)

    def test_invalid(self):
        assert _km_float("") == -1.0
        assert _km_float("N/A") == -1.0


class TestResolveKmRange:
    def _make_section(self, road, direction, start_km, end_km, sec_start, sec_end):
        return {
            "RoadName": road,
            "RoadDirection": direction,
            "SectionMile": {"StartKM": start_km, "EndKM": end_km},
            "RoadSection": {"Start": sec_start, "End": sec_end},
        }

    def test_found_range(self):
        sections = [
            self._make_section("國道1號", "N", "346K+000", "349K+400", "岡山", "高科"),
            self._make_section("國道1號", "N", "356K+200", "362K+400", "楠梓", "鼎金"),
            self._make_section("國道1號", "N", "349K+400", "356K+200", "高科", "楠梓"),
        ]
        km_min, km_max = _resolve_km_range(sections, "國道1號", "N", "岡山", "楠梓")
        assert km_min == pytest.approx(346.0)
        # 楠梓同時出現在「高科→楠梓」(end) 和「楠梓→鼎金」(start)，max 取 EndKM 362.4
        assert km_max == pytest.approx(362.4)

    def test_not_found(self):
        sections = [
            self._make_section("國道3號", "N", "10K+000", "20K+000", "A", "B"),
        ]
        km_min, km_max = _resolve_km_range(sections, "國道1號", "N", "中正", "岡山")
        assert km_min == -1.0


# ---------------------------------------------------------------------------
# query_segment — mock TDX API
# ---------------------------------------------------------------------------

_MOCK_SECTIONS = [
    {
        "SectionID": "0146",
        "RoadName": "國道1號", "RoadDirection": "N",
        "SectionMile": {"StartKM": "349K+400", "EndKM": "356K+200"},
        "RoadSection": {"Start": "楠梓", "End": "岡山"},
    },
    {
        "SectionID": "0148",
        "RoadName": "國道1號", "RoadDirection": "N",
        "SectionMile": {"StartKM": "356K+200", "EndKM": "362K+400"},
        "RoadSection": {"Start": "鼎金", "End": "楠梓"},
    },
]

_MOCK_EVENTS_EMPTY = []

_MOCK_EVENTS_WITH_ACCIDENT = [
    {
        "EventID": "TEST-001",
        "EventTitle": "事故",
        "Description": "國道1號 北向 352K+000 車輛事故",
        "EventType": 1,
        "EventSubType": 100,
        "EventStep": 1,
        "EffectiveTime": "2026-05-19T10:00:00+08:00",
        "Location": {
            "FreeExpressHighway": {
                "Road": "國道1號", "Direction": "北向",
                "StartKM": "352K+000", "EndKM": "352K+500",
                "SectionStart": "楠梓", "SectionEnd": "岡山",
            }
        },
        "Impact": {"Severity": 2, "BlockWay": 1, "BlockedLanes": "1", "Regulations": [1], "Description": "封閉一線"},
    }
]

_MOCK_LIVE = [
    {
        "SectionID": "0146",
        "TravelSpeed": 90.0, "TravelTime": 277,
        "CongestionLevelID": "A", "CongestionLevel": "1",
    },
    {
        "SectionID": "0148",
        "TravelSpeed": 84.0, "TravelTime": 260,
        "CongestionLevelID": "A", "CongestionLevel": "1",
    },
]


def _make_resp(data):
    r = MagicMock()
    r.data = data
    return r


def _mock_client_factory(events):
    def _get(url, params=None):
        if "Section/Freeway" in url:
            return _make_resp({"Sections": _MOCK_SECTIONS})
        if "RoadEvent" in url:
            return _make_resp({"LiveEvents": events})
        if "Live/Freeway" in url:
            return _make_resp({"LiveTraffics": _MOCK_LIVE})
        return _make_resp({})
    return _get


class TestQuerySegment:
    def _make_mocks(self, events):
        mock_auth = MagicMock()
        mock_client = MagicMock()
        mock_client.get.side_effect = _mock_client_factory(events)
        return mock_auth, mock_client

    def _run(self, events, *args, **kwargs):
        """Import module fresh (after conftest reloads tools.*), then call query_segment."""
        import tools.freeway_query as fq
        mock_auth, mock_client = self._make_mocks(events)
        with patch.object(fq, "TdxAuthManager", return_value=mock_auth), \
             patch.object(fq, "TdxClient", return_value=mock_client):
            return fq.query_segment(*args, **kwargs)

    def test_no_events(self):
        result = self._run(_MOCK_EVENTS_EMPTY, "國道1號", "北向", "中正交流道", "岡山交流道")
        assert result["status"] == "ok"
        assert result["event_count"] == 0
        assert "無事故" in result["summary"]

    def test_with_accident(self):
        result = self._run(_MOCK_EVENTS_WITH_ACCIDENT, "國道1號", "北向", "中正交流道", "岡山交流道")
        assert result["event_count"] == 1
        assert result["events"][0]["type"] == "事故"
        assert result["events"][0]["step"] == "發生中"
        assert result["events"][0]["severity"] == "中等"

    def test_sections_returned(self):
        result = self._run(_MOCK_EVENTS_EMPTY, "國道1號", "北向", "中正交流道", "岡山交流道")
        assert len(result["sections"]) > 0
        s = result["sections"][0]
        assert "speed_kmh" in s
        assert "congestion" in s

    def test_output_schema(self):
        result = self._run(_MOCK_EVENTS_EMPTY, "國道1號", "北向", "中正交流道", "岡山交流道")
        for key in ("status", "road", "direction", "from_ic", "to_ic",
                    "km_range", "summary", "events", "event_count", "sections"):
            assert key in result

    def test_normalize_ic_in_query(self):
        """不帶「交流道」後綴也能查詢。"""
        result = self._run(_MOCK_EVENTS_EMPTY, "國道1號", "北向", "中正", "岡山")
        assert result["status"] == "ok"
