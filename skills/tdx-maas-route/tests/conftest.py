"""tdx-maas-route 測試共用 fixture。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 確保 repo root 在 sys.path（runtime.tdx.* 可用）
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 將 skill 目錄加入 sys.path，讓 tests 可直接 import tools.*
SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from runtime.tdx.tdx_config import TDXConfig  # noqa: E402

CONFIG_PATH = REPO_ROOT / "runtime" / "tdx" / "config.json"


@pytest.fixture()
def config() -> TDXConfig:
    """提供 TDXConfig 實例。"""
    return TDXConfig(CONFIG_PATH)
