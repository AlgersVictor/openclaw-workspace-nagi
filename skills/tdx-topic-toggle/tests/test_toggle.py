"""tdx-topic-toggle unit tests。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import importlib.machinery
import importlib.util

import pytest

_SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SKILL_ROOT.parent / "tdx-mqtt-listener"))
sys.path.insert(0, str(_SKILL_ROOT))

from tools.topic_groups import GROUPS, DEFAULT_CONFIG, load_config, save_config, get_extra_topics


def _import_bin():
    """bin/tdx-topic-toggle 有連字號，用 importlib 載入。"""
    bin_path = _SKILL_ROOT / "bin" / "tdx-topic-toggle"
    loader = importlib.machinery.SourceFileLoader("tdx_topic_toggle", str(bin_path))
    spec = importlib.util.spec_from_loader("tdx_topic_toggle", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# topic_groups helpers
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        cfg = load_config(tmp_path / "no_such.json")
        assert cfg == DEFAULT_CONFIG

    def test_reads_existing_file(self, tmp_path):
        p = tmp_path / "groups.json"
        p.write_text(json.dumps({"taipei": True, "tainan": False}))
        cfg = load_config(p)
        assert cfg["taipei"] is True
        assert cfg["tainan"] is False

    def test_missing_key_defaults_false(self, tmp_path):
        p = tmp_path / "groups.json"
        p.write_text("{}")
        cfg = load_config(p)
        for group in GROUPS:
            assert cfg[group] is False

    def test_corrupt_file_returns_defaults(self, tmp_path):
        p = tmp_path / "groups.json"
        p.write_text("not json")
        cfg = load_config(p)
        assert cfg == DEFAULT_CONFIG


class TestSaveConfig:
    def test_creates_parent_dir(self, tmp_path):
        p = tmp_path / "nested" / "dir" / "groups.json"
        save_config(p, {"taipei": True})
        assert p.exists()
        assert json.loads(p.read_text())["taipei"] is True

    def test_roundtrip(self, tmp_path):
        p = tmp_path / "groups.json"
        original = {k: (i % 2 == 0) for i, k in enumerate(GROUPS)}
        save_config(p, original)
        loaded = load_config(p)
        assert loaded == original


class TestGetExtraTopics:
    def test_all_disabled_returns_empty(self):
        cfg = {k: False for k in GROUPS}
        assert get_extra_topics(cfg) == []

    def test_taipei_enabled_returns_taipei_topics(self):
        cfg = {k: False for k in GROUPS}
        cfg["taipei"] = True
        extra = get_extra_topics(cfg)
        assert "v2/Bus/Alert/City/Taipei" in extra
        assert "v2/Bus/Alert/City/NewTaipei" in extra
        assert "v2/Rail/Metro/Alert/TRTC" in extra

    def test_multiple_groups_returns_all_topics(self):
        cfg = {k: False for k in GROUPS}
        cfg["taipei"] = True
        cfg["taichung"] = True
        extra = get_extra_topics(cfg)
        assert "v2/Bus/Alert/City/Taipei" in extra
        assert "v2/Bus/Alert/City/Taichung" in extra

    def test_no_duplicates(self):
        cfg = {k: True for k in GROUPS}
        extra = get_extra_topics(cfg)
        assert len(extra) == len(set(extra))


# ---------------------------------------------------------------------------
# cmd_toggle
# ---------------------------------------------------------------------------

class TestCmdToggle:
    def _make_args(self, tmp_path, action, group, no_restart=True):
        return SimpleNamespace(
            config=str(tmp_path / "groups.json"),
            action=action,
            group=group,
            no_restart=no_restart,
        )

    def test_enable_sets_group_true(self, tmp_path, capsys):
        cmd_toggle = _import_bin().cmd_toggle
        args = self._make_args(tmp_path, "enable", "taipei")
        rc = cmd_toggle(args)
        assert rc == 0
        cfg = load_config(Path(args.config))
        assert cfg["taipei"] is True
        out = json.loads(capsys.readouterr().out.split("\n[")[0])
        assert out["status"] == "ok"
        assert out["state"] == "開啟"

    def test_disable_sets_group_false(self, tmp_path, capsys):
        cmd_toggle = _import_bin().cmd_toggle
        p = Path(tmp_path / "groups.json")
        save_config(p, {"taipei": True})
        args = self._make_args(tmp_path, "disable", "taipei")
        cmd_toggle(args)
        cfg = load_config(p)
        assert cfg["taipei"] is False

    def test_restart_called_when_no_restart_false(self, tmp_path):
        cmd_toggle = _import_bin().cmd_toggle
        args = self._make_args(tmp_path, "enable", "taichung", no_restart=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            cmd_toggle(args)
            mock_run.assert_called_once()

    def test_no_restart_skips_systemctl(self, tmp_path):
        cmd_toggle = _import_bin().cmd_toggle
        args = self._make_args(tmp_path, "enable", "taichung", no_restart=True)
        with patch("subprocess.run") as mock_run:
            cmd_toggle(args)
            mock_run.assert_not_called()

    def test_restart_fail_warns_but_returns_0(self, tmp_path, capsys):
        cmd_toggle = _import_bin().cmd_toggle
        args = self._make_args(tmp_path, "enable", "keelung", no_restart=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Unit not found")
            rc = cmd_toggle(args)
            assert rc == 0


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------

class TestCmdStatus:
    def test_status_shows_all_groups(self, tmp_path, capsys):
        cmd_status = _import_bin().cmd_status
        args = SimpleNamespace(config=str(tmp_path / "groups.json"))
        cmd_status(args)
        rows = json.loads(capsys.readouterr().out)
        assert len(rows) == len(GROUPS)
        names = {r["group"] for r in rows}
        assert names == set(GROUPS.keys())

    def test_status_reflects_saved_config(self, tmp_path, capsys):
        cmd_status = _import_bin().cmd_status
        p = tmp_path / "groups.json"
        save_config(p, {**{k: False for k in GROUPS}, "taipei": True})
        args = SimpleNamespace(config=str(p))
        cmd_status(args)
        rows = json.loads(capsys.readouterr().out)
        taipei = next(r for r in rows if r["group"] == "taipei")
        assert taipei["enabled"] is True
