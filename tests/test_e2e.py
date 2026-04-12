import json, subprocess, sys
from pathlib import Path

def test_cli_pre_tool_use_allow(tmp_path):
    (tmp_path / ".claude" / "dynamic-prompt-harness").mkdir(parents=True)
    (tmp_path / ".claude" / "dynamic-prompt-harness" / "registry.json").write_text(
        json.dumps({"version": 1, "entries": []}), encoding="utf-8")
    stdin = json.dumps({"session_id":"s","cwd":str(tmp_path),"transcript_path":"",
                        "hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{}})
    proc = subprocess.run(
        [sys.executable, "-m", "dynamic_prompt_harness", "pre_tool_use"],
        input=stdin, capture_output=True, text=True, cwd=str(tmp_path), timeout=10)
    assert proc.returncode == 0
    assert proc.stdout == ""
