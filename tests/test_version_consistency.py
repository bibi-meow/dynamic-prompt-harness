"""Guard rail: pyproject, plugin.json, and CHANGELOG top entry must agree."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def _plugin_version() -> str:
    data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return data["version"]


def _changelog_top_version() -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s+\[(\d+\.\d+\.\d+)\]", text, flags=re.MULTILINE)
    assert m is not None, "no version section found in CHANGELOG.md"
    return m.group(1)


def test_all_three_version_sources_agree():
    py = _pyproject_version()
    pl = _plugin_version()
    cl = _changelog_top_version()
    assert py == pl == cl, f"version drift: pyproject={py!r} plugin={pl!r} changelog={cl!r}"
