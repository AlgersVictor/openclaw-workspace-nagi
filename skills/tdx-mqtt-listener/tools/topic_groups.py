"""TDX MQTT 可切換 Topic 群組定義與設定檔讀寫。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 群組 → topics 對照表
GROUPS: dict[str, list[str]] = {
    "taipei": [
        "v2/Bus/Alert/City/Taipei",
        "v2/Bus/Alert/City/NewTaipei",
        "v2/Rail/Metro/Alert/TRTC",
    ],
    "taichung": [
        "v2/Bus/Alert/City/Taichung",
        "v2/Rail/Metro/Alert/TMRT",
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
