"""將 TDX MQTT payload 格式化為 Discord Embed。"""

from __future__ import annotations

import time
from typing import Any

_COLOR_RED    = 15158332   # 通阻（紅）
_COLOR_YELLOW = 16776960   # 恢復/輕微（黃）
_COLOR_GREEN  = 3066993    # 正常（綠）

_TOPIC_LABEL: dict[str, str] = {
    "Bus/News":        "公車最新消息",
    "Bus/Alert":       "公車營運通阻",
    "Rail/TRA/Alert":  "臺鐵動態通阻",
    "Rail/THSR":       "高鐵即時通阻",
    "Rail/Metro":      "捷運/輕軌通阻",
    "Ship/Alert":      "航運通阻",
}


def _topic_label(topic: str) -> str:
    for key, label in _TOPIC_LABEL.items():
        if key in topic:
            return label
    return "TDX 通阻通知"


def _ts_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _extract_text(payload: Any, keys: list[str]) -> str:
    """從 payload dict 依優先順序取文字欄位。"""
    if not isinstance(payload, dict):
        return str(payload)
    for k in keys:
        val = payload.get(k)
        if val:
            return str(val)
    return "(無說明)"


def format_embed(topic: str, payload: Any) -> dict[str, Any]:
    """將單筆 MQTT 訊息轉為 Discord Embed dict。"""
    label = _topic_label(topic)

    # 嘗試提取標題與說明（各 API payload 欄位名稱不同）
    title_text = _extract_text(payload, [
        "Title", "AlertTitle", "Subject", "NewsTitle",
        "AlertType", "EventType", "Type",
    ])
    desc_text = _extract_text(payload, [
        "Description", "AlertMessage", "Content", "NewsContent",
        "Detail", "Message", "Summary",
    ])

    # 顏色：有 Status/IsAlerted=false 或 title 含「恢復」視為恢復
    color = _COLOR_RED
    if isinstance(payload, dict):
        status = str(payload.get("Status", payload.get("IsAlerted", ""))).lower()
        if status in ("false", "0", "resolved", "normal"):
            color = _COLOR_GREEN
        elif "恢復" in title_text or "恢復" in desc_text:
            color = _COLOR_GREEN

    fields: list[dict[str, Any]] = [
        {"name": "Topic", "value": f"`{topic}`", "inline": False},
    ]

    # 附加有用欄位
    if isinstance(payload, dict):
        for key in ("StartTime", "EndTime", "RouteID", "StationID", "Direction"):
            val = payload.get(key)
            if val:
                fields.append({"name": key, "value": str(val), "inline": True})

    return {
        "title": f"[{label}] {title_text}",
        "description": desc_text,
        "color": color,
        "fields": fields,
        "footer": {"text": f"TDX MQTT  ·  {_ts_now()}"},
    }
