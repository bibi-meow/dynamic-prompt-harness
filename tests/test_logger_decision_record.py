"""Dispatcher must emit exactly one dph_decision JSONL record per invocation."""
import json
import sys
from pathlib import Path
from dynamic_prompt_harness.dispatcher import Dispatcher


def test_single_dph_decision_event_with_all_fields(tmp_path, monkeypatch):
    reg = {
        "version": 1,
        "entries": [
            {"id": "x1", "triggers": ["pre_tool_use"],
             "command": [sys.executable, "-c",
                         "import json;print(json.dumps({'decision':'allow'}))"]},
            {"id": "x2", "triggers": ["pre_tool_use"],
             "command": [sys.executable, "-c",
                         "import json;print(json.dumps({'decision':'hint','message':'fyi'}))"]},
        ],
    }
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(reg), encoding="utf-8")
    log_path = tmp_path / "dph.log"
    monkeypatch.setenv("DPH_REGISTRY_PATH", str(reg_path))
    monkeypatch.setenv("DPH_LOG_PATH", str(log_path))

    Dispatcher(tmp_path).run_capture(
        "pre_tool_use",
        json.dumps({"tool_name": "Bash", "tool_input": {}}),
    )

    records = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    decision_events = [r for r in records if r["event"] == "dph_decision"]
    assert len(decision_events) == 1

    d = decision_events[0]
    for k in ("trigger", "matched_entries", "per_entry_outcomes",
              "final_decision", "final_message", "latency_ms"):
        assert k in d, f"missing field: {k}"

    assert d["trigger"] == "pre_tool_use"
    assert d["matched_entries"] == ["x1", "x2"]
    assert len(d["per_entry_outcomes"]) == 2
    for o in d["per_entry_outcomes"]:
        assert set(o.keys()) >= {"id", "decision", "message", "metadata", "duration_ms"}
    assert d["final_decision"] == "hint"
    assert d["final_message"] == "fyi"
    assert isinstance(d["latency_ms"], (int, float))
    assert d["latency_ms"] >= 0
