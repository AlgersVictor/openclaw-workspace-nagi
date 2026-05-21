"""Workspace-level conftest: 隔離各 skill 的 tools 包，避免跨 skill sys.modules 快取碰撞。"""
import importlib
import sys
from pathlib import Path

import pytest

_SKILLS_ROOT = Path(__file__).resolve().parent / "skills"

_SKILL_PATHS: dict[str, str] = {
    d.name: str(d)
    for d in _SKILLS_ROOT.iterdir()
    if d.is_dir()
}


def _skill_root_for(file_path: Path) -> str | None:
    for root in _SKILL_PATHS.values():
        if str(file_path).startswith(root):
            return root
    return None


def _activate_skill_tools(skill_root: str) -> None:
    """清除 tools 快取，切換 sys.path，強制重新載入。"""
    for key in list(sys.modules.keys()):
        if key == "tools" or key.startswith("tools."):
            del sys.modules[key]
    if skill_root in sys.path:
        sys.path.remove(skill_root)
    sys.path.insert(0, skill_root)
    try:
        importlib.import_module("tools")
    except ImportError:
        pass


def pytest_collect_file(parent, file_path):
    """collection 時切換 tools。"""
    skill_root = _skill_root_for(file_path)
    if skill_root:
        _activate_skill_tools(skill_root)


@pytest.fixture(autouse=True)
def _skill_tools_isolation(request):
    """每個 test 執行前確保 tools 指向正確的 skill。"""
    skill_root = _skill_root_for(Path(str(request.fspath)))
    if skill_root:
        _activate_skill_tools(skill_root)
    yield
