import json, pytest
from pathlib import Path
from dynamic_prompt_harness.core.registry import Registry
from dynamic_prompt_harness.core.errors import RegistryError

def _write(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p

def test_load_and_filter_by_trigger(tmp_path):
    p = _write(tmp_path, {"version": 1, "entries": [
        {"id": "a", "triggers": ["pre_tool_use"], "command": ["x"], "priority": 10},
        {"id": "b", "triggers": ["post_tool_use"], "command": ["y"], "priority": 0},
        {"id": "c", "triggers": ["pre_tool_use"], "command": ["z"], "priority": 5},
    ]})
    r = Registry.load(p)
    got = r.entries_for("pre_tool_use", tool=None)
    assert [e.id for e in got] == ["a", "c"]  # priority desc

def test_missing_file_raises(tmp_path):
    with pytest.raises(RegistryError):
        Registry.load(tmp_path / "nope.json")

def test_empty_entries(tmp_path):
    p = _write(tmp_path, {"version": 1, "entries": []})
    r = Registry.load(p)
    assert r.entries_for("pre_tool_use", None) == []

def test_matcher_filter(tmp_path):
    p = _write(tmp_path, {"version": 1, "entries": [
        {"id": "a", "triggers": ["pre_tool_use"], "command": ["x"], "matcher": "Write|Edit"},
        {"id": "b", "triggers": ["pre_tool_use"], "command": ["y"]},
    ]})
    r = Registry.load(p)
    assert [e.id for e in r.entries_for("pre_tool_use", "Write")] == ["a", "b"]
    assert [e.id for e in r.entries_for("pre_tool_use", "Bash")] == ["b"]
