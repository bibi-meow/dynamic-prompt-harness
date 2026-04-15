"""One test per schema invariant. Covers the five E_* error codes."""
import json
import pytest
from pathlib import Path
from dynamic_prompt_harness.core.registry import Registry
from dynamic_prompt_harness.core.errors import RegistryError


def _write(tmp_path: Path, entries: list) -> Path:
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"version": 1, "entries": entries}), encoding="utf-8")
    return p


def test_invalid_matcher_fails_load(tmp_path):
    p = _write(tmp_path, [{
        "id": "e", "triggers": ["pre_tool_use"],
        "command": ["echo", "hi"], "matcher": "(unterminated",
    }])
    with pytest.raises(RegistryError) as exc:
        Registry.load(p)
    assert exc.value.code == "E_BAD_MATCHER"


def test_duplicate_id_fails_load(tmp_path):
    p = _write(tmp_path, [
        {"id": "dup", "triggers": ["pre_tool_use"], "command": ["echo", "1"]},
        {"id": "dup", "triggers": ["pre_tool_use"], "command": ["echo", "2"]},
    ])
    with pytest.raises(RegistryError) as exc:
        Registry.load(p)
    assert exc.value.code == "E_DUPLICATE_ID"


def test_negative_timeout_fails_load(tmp_path):
    p = _write(tmp_path, [{
        "id": "e", "triggers": ["pre_tool_use"],
        "command": ["echo", "hi"], "timeout_sec": -0.5,
    }])
    with pytest.raises(RegistryError) as exc:
        Registry.load(p)
    assert exc.value.code == "E_BAD_TIMEOUT"


def test_unknown_log_level_fails_load(tmp_path):
    p = _write(tmp_path, [{
        "id": "e", "triggers": ["pre_tool_use"],
        "command": ["echo", "hi"], "log_level": "trace",
    }])
    with pytest.raises(RegistryError) as exc:
        Registry.load(p)
    assert exc.value.code == "E_BAD_LOG_LEVEL"


def test_non_string_command_element_fails_load(tmp_path):
    p = _write(tmp_path, [{
        "id": "e", "triggers": ["pre_tool_use"],
        "command": ["echo", 42],
    }])
    with pytest.raises(RegistryError) as exc:
        Registry.load(p)
    assert exc.value.code == "E_BAD_COMMAND"
