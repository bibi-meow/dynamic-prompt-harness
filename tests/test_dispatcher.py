import json, sys
from pathlib import Path
from dynamic_prompt_harness.dispatcher import Dispatcher

def _setup(tmp_path, entries):
    reg_dir = tmp_path / ".claude" / "dynamic-prompt-harness"
    reg_dir.mkdir(parents=True)
    (reg_dir / "registry.json").write_text(
        json.dumps({"version": 1, "entries": entries}), encoding="utf-8")
    return tmp_path

def test_empty_registry_allows(tmp_path):
    base = _setup(tmp_path, [])
    stdin = json.dumps({"session_id":"s","cwd":str(base),"transcript_path":"",
                        "hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{}})
    d = Dispatcher(base=base)
    out, rc = d.run_capture("pre_tool_use", stdin)
    assert rc == 0 and out == ""

def test_deny_propagates(tmp_path):
    code = 'import json,sys; json.dump({"decision":"deny","message":"stop"}, sys.stdout)'
    base = _setup(tmp_path, [{
        "id": "t", "triggers": ["pre_tool_use"],
        "command": [sys.executable, "-c", code],
    }])
    stdin = json.dumps({"session_id":"s","cwd":str(base),"transcript_path":"",
                        "hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{}})
    out, rc = Dispatcher(base=base).run_capture("pre_tool_use", stdin)
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_missing_registry_fails_safe_allow(tmp_path):
    # no registry.json exists
    stdin = json.dumps({"session_id":"s","cwd":str(tmp_path),"transcript_path":"",
                        "hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{}})
    out, rc = Dispatcher(base=tmp_path).run_capture("pre_tool_use", stdin)
    assert rc == 0 and out == ""


def test_run_capture_evaluates_all_entries_despite_deny(tmp_path, monkeypatch):
    """Dispatcher must not short-circuit on first DENY; all matching entries run."""
    import json, sys
    from dynamic_prompt_harness.dispatcher import Dispatcher

    marker = tmp_path / "second_ran.txt"
    registry = {
        "version": 1,
        "entries": [
            {
                "id": "first-deny",
                "triggers": ["pre_tool_use"],
                "command": [sys.executable, "-c",
                           "import json,sys; print(json.dumps({'decision':'deny','message':'first says no'}))"],
            },
            {
                "id": "second-allow",
                "triggers": ["pre_tool_use"],
                "command": [sys.executable, "-c",
                           f"open(r'{marker}','w').write('yes'); "
                           "import json; print(json.dumps({'decision':'allow'}))"],
            },
        ],
    }
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setenv("DPH_REGISTRY_PATH", str(reg_path))
    monkeypatch.setenv("DPH_LOG_PATH", str(tmp_path / "dph.log"))

    d = Dispatcher(tmp_path)
    d.run_capture("pre_tool_use", json.dumps({"tool_name": "Bash", "tool_input": {}}))

    assert marker.exists(), "second entry must execute even after first DENY"
