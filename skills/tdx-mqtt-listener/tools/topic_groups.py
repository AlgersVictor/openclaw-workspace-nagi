"""TDX MQTT 可切換 Topic 群組定義與設定檔讀寫。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 群組 → topics 對照表
GROUPS: dict[str, list[str]] = {
    # ── 北部 ──
    "taipei": [
        "v2/Bus/Alert/City/Taipei",
        "v2/Bus/Alert/City/NewTaipei",
        "v2/Rail/Metro/Alert/TRTC",    # 台北捷運（含環狀線）
        "v2/Rail/Metro/Alert/NTDLRT",  # 淡海輕軌（新北）
    ],
    "keelung": [
        "v2/Bus/Alert/City/Keelung",
        "v2/Rail/Metro/Alert/KLRT",    # 基隆輕軌
    ],
    "taoyuan": [
        "v2/Bus/Alert/City/Taoyuan",
        "v2/Rail/Metro/Alert/TYMC",    # 桃園捷運
    ],
    "hsinchu": [
        "v2/Bus/Alert/City/Hsinchu",
        "v2/Bus/Alert/City/HsinchuCounty",
    ],
    # ── 中部 ──
    "miaoli": [
        "v2/Bus/Alert/City/MiaoliCounty",
    ],
    "taichung": [
        "v2/Bus/Alert/City/Taichung",
        "v2/Rail/Metro/Alert/TMRT",    # 台中捷運
    ],
    "changhua": [
        "v2/Bus/Alert/City/ChanghuaCounty",
    ],
    "nantou": [
        "v2/Bus/Alert/City/NantouCounty",
    ],
    "yunlin": [
        "v2/Bus/Alert/City/YunlinCounty",
    ],
    # ── 南部 ──
    "chiayi": [
        "v2/Bus/Alert/City/Chiayi",
        "v2/Bus/Alert/City/ChiayiCounty",
    ],
    "tainan": [
        "v2/Bus/Alert/City/Tainan",
    ],
    "kaohsiung": [
        "v2/Bus/Alert/City/Kaohsiung",
        "v2/Rail/Metro/Alert/KRTC",    # 高雄捷運
    ],
    "pingtung": [
        "v2/Bus/Alert/City/PingtungCounty",
    ],
    # ── 東部 ──
    "yilan": [
        "v2/Bus/Alert/City/YilanCounty",
    ],
    "hualien": [
        "v2/Bus/Alert/City/HualienCounty",
    ],
    "taitung": [
        "v2/Bus/Alert/City/TaitungCounty",
    ],
    # ── 離島 ──
    "penghu": [
        "v2/Bus/Alert/City/PenghuCounty",
    ],
    "kinmen": [
        "v2/Bus/Alert/City/KinmenCounty",
    ],
    "lienchiang": [
        "v2/Bus/Alert/City/LienchiangCounty",
    ],
}

DEFAULT_CONFIG: dict[str, bool] = {k: False for k in GROUPS}


def load_config(path: Path) -> dict[str, bool]:
    """讀取群組設定檔，不存在時回傳預設值。"""
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: bool(data.get(k, False)) for k in GROUPS}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(path: Path, config: dict[str, bool]) -> None:
    """寫入群組設定檔。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get_extra_topics(config: dict[str, bool]) -> list[str]:
    """回傳所有已啟用群組的 topics。"""
    topics: list[str] = []
    for group, enabled in config.items():
        if enabled:
            topics.extend(GROUPS.get(group, []))
    return topics
