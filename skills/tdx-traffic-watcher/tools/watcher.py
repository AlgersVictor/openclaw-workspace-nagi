"""交通事件監視器主迴圈。"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

_SHARED = Path(__file__).resolve().parents[2] / "tdx-shared-core"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from tdx_auth import TdxAuthError, TdxAuthManager  # noqa: E402
from tdx_client import TdxClient  # noqa: E402

from tools.discord_notifier import DiscordNotifyError, send_embed
from tools.event_differ import diff_congestion, diff_events
from tools.traffic_formatter import (
    CITY_LABELS,
    format_congestion_alert,
    format_congestion_clear,
    format_new_event,
    format_resolved_event,
)
from tools.event_dedup import EventDedup
from tools.freeway_sections import event_passes_section_filter, get_default_sections
from tools.traffic_poller import poll_city_events, poll_city_live, poll_freeway_events

TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"

_RUNTIME = Path.home() / ".openclaw/workspace/runtime/tdx"
_CONFIG_FILE = _RUNTIME / "traffic_watcher_config.json"
_STATE_FILE = _RUNTIME / "traffic_watcher_state.json"
_DEDUP_FILE = _RUNTIME / "traffic_dedup_state.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "freeway": False,
    "freeway_sections": None,  # None 表示使用 get_default_sections()（全開）
    "cities": {"Kaohsiung": True},
    "congestion_alert_threshold": 0.35,
    "congestion_clear_threshold": 0.10,
}

logger = logging.getLogger("tdx-traffic-watcher")


def load_config() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        return dict(_DEFAULT_CONFIG)
    with open(_CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
    result = dict(_DEFAULT_CONFIG)
    result.update(cfg)
    return result


def load_state() -> dict[str, Any]:
    if not _STATE_FILE.exists():
        return {"freeway_events": {}, "city_events": {}, "city_congestion": {}}
    with open(_STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any]) -> None:
    _RUNTIME.mkdir(parents=True, exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


_NOTIFY_INTERVAL = 0.6  # Discord webhook 限速保護：每則間隔 0.6 秒


def _notify(embed: dict[str, Any], dry_run: bool) -> None:
    try:
        send_embed(embed, dry_run=dry_run)
        if not dry_run:
            time.sleep(_NOTIFY_INTERVAL)
    except DiscordNotifyError as exc:
        logger.warning("Discord 通知失敗：%s", exc)


def run_once(*, dry_run: bool = False) -> None:
    """執行單次 poll cycle。"""
    config = load_config()
    state = load_state()
    client = TdxClient(TdxAuthManager(TOKEN_URL))
    dedup = EventDedup(_DEDUP_FILE, ttl_hours=24.0)

    # 國道事件（依路段篩選）
    if config.get("freeway"):
        sections_config = config.get("freeway_sections") or get_default_sections()
        try:
            new_events = poll_freeway_events(client)
            old = state.get("freeway_events", {})
            new_items, resolved_ids = diff_events(old, new_events)
            for item in new_items:
                if event_passes_section_filter(item, sections_config):
                    pt = item.get("publish_time", "")
                    title = item.get("title") or ""
                    if not dedup.is_duplicate(pt, title):
                        _notify(format_new_event(item, "國道"), dry_run)
                        dedup.mark_sent(pt, title)
            for eid in resolved_ids:
                old_item = old.get(eid, {})
                if event_passes_section_filter(old_item, sections_config):
                    _notify(format_resolved_event(old_item, eid, "國道"), dry_run)
            # 只追蹤啟用路段的事件（路段重啟時可重新通報）
            state["freeway_events"] = {
                e["event_id"]: e
                for e in new_events
                if e.get("event_id") and event_passes_section_filter(e, sections_config)
            }
        except Exception as exc:
            logger.error("國道事件 poll 失敗：%s", exc)

    # 各縣市事件 + 路況
    state.setdefault("city_events", {})
    state.setdefault("city_congestion", {})

    for city, enabled in config.get("cities", {}).items():
        if not enabled:
            continue
        label = CITY_LABELS.get(city, city)

        try:
            new_events = poll_city_events(client, city)
            old = state["city_events"].get(city, {})
            new_items, resolved_ids = diff_events(old, new_events)
            for item in new_items:
                pt = item.get("publish_time", "")
                title = item.get("title") or ""
                if not dedup.is_duplicate(pt, title):
                    _notify(format_new_event(item, label), dry_run)
                    dedup.mark_sent(pt, title)
            for eid in resolved_ids:
                _notify(format_resolved_event(old.get(eid, {}), eid, label), dry_run)
            state["city_events"][city] = {e["event_id"]: e for e in new_events if e.get("event_id")}
        except Exception as exc:
            logger.error("%s 事件 poll 失敗：%s", city, exc)

        try:
            live = poll_city_live(client, city)
            ratio = live.get("congestion_ratio", 0.0)
            old_cong = state["city_congestion"].get(city, {"alerted": False, "ratio": 0.0})
            action = diff_congestion(
                old_ratio=old_cong.get("ratio", 0.0),
                new_ratio=ratio,
                currently_alerted=old_cong.get("alerted", False),
                threshold_high=float(config.get("congestion_alert_threshold", 0.35)),
                threshold_low=float(config.get("congestion_clear_threshold", 0.10)),
            )
            if action == "alert":
                _notify(format_congestion_alert(label, ratio, live.get("worst_segments", [])), dry_run)
                state["city_congestion"][city] = {"alerted": True, "ratio": ratio}
            elif action == "clear":
                _notify(format_congestion_clear(label), dry_run)
                state["city_congestion"][city] = {"alerted": False, "ratio": ratio}
            else:
                state["city_congestion"][city] = {
                    "alerted": old_cong.get("alerted", False),
                    "ratio": ratio,
                }
        except Exception as exc:
            logger.error("%s 路況 poll 失敗：%s", city, exc)

    dedup.save()
    save_state(state)


def run_daemon(interval_seconds: int = 300, *, dry_run: bool = False) -> None:
    """持續監控，每 interval_seconds 秒執行一次 poll。"""
    logger.info("traffic-watcher 啟動，間隔 %d 秒", interval_seconds)
    while True:
        try:
            run_once(dry_run=dry_run)
        except TdxAuthError as exc:
            logger.error("TDX 認證失敗，停止：%s", exc)
            raise
        except Exception as exc:
            logger.error("poll cycle 例外：%s", exc)
        time.sleep(interval_seconds)
