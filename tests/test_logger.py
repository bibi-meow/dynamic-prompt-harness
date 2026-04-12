import json
from dynamic_prompt_harness.core.logger import JsonlLogger

def test_append_jsonl(tmp_path):
    p = tmp_path / "x.log"
    lg = JsonlLogger(p, level="info")
    lg.log("info", "hello", k=1)
    lg.log("debug", "skipped", k=2)  # below default info→but we test level gating separately
    lines = p.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    assert first["event"] == "hello" and first["level"] == "info" and first["k"] == 1

def test_level_gating(tmp_path):
    p = tmp_path / "y.log"
    lg = JsonlLogger(p, level="error")
    lg.log("info", "skip")
    lg.log("error", "keep")
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["event"] == "keep"
