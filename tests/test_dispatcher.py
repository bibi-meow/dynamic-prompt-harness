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
