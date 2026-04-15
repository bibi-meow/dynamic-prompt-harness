"""End-to-end test: two denies + one allow are ALL evaluated,
final metadata aggregates per-entry evidence, messages joined with "; "."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from dynamic_prompt_harness.dispatcher import Dispatcher


def _make_registry(tmp_path: Path) -> Path:
    reg = {
        "version": 1,
        "entries": [
            {
                "id": "deny-a",
                "triggers": ["pre_tool_use"],
                "command": [
                    sys.executable, "-c",
                    "import json,sys; print(json.dumps({"
                    "'decision':'deny','message':'A violated','metadata':{'rule':'A'}"
                    "}))",
                ],
            },
            {
                "id": "allow-ok",
                "triggers": ["pre_tool_use"],
                "command": [
                    sys.executable, "-c",
                    "import json; print(json.dumps({"
                    "'decision':'allow','metadata':{'checked':True}"
                    "}))",
                ],
            },
            {
                "id": "deny-c",
                "triggers": ["pre_tool_use"],
                "command": [
                    sys.executable, "-c",
                    "import json; print(json.dumps({"
                    "'decision':'deny','message':'C violated','metadata':{'rule':'C'}"
                    "}))",
                ],
            },
        ],
    }
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(reg), encoding="utf-8")
    return p


def test_full_evaluation_aggregates_evidence(tmp_path, monkeypatch):
    reg_path = _make_registry(tmp_path)
    log_path = tmp_path / "dph.log"
    monkeypatch.setenv("DPH_REGISTRY_PATH", str(reg_path))
    monkeypatch.setenv("DPH_LOG_PATH", str(log_path))

    d = Dispatcher(tmp_path)
    out, _rc = d.run_capture(
        "pre_tool_use",
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
    )

    out_json = json.loads(out)
    flat = json.dumps(out_json)
    assert "A violated" in flat
    assert "C violated" in flat
    assert "A violated; C violated" in flat or flat.count("; ") >= 1

    records = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    decision = next(r for r in records if r["event"] == "dph_decision")
    ids = [o["id"] for o in decision["per_entry_outcomes"]]
    assert ids == ["deny-a", "allow-ok", "deny-c"]
    decisions = [o["decision"] for o in decision["per_entry_outcomes"]]
    assert decisions == ["deny", "allow", "deny"]
    metas = {o["id"]: o["metadata"] for o in decision["per_entry_outcomes"]}
    assert metas["deny-a"] == {"rule": "A"}
    assert metas["allow-ok"] == {"checked": True}
    assert metas["deny-c"] == {"rule": "C"}
    assert decision["final_decision"] == "deny"
    assert decision["final_message"] == "A violated; C violated"
