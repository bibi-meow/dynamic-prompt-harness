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


def test_logger_accepts_warning_as_canonical_and_warn_as_alias(tmp_path):
    import json

    from dynamic_prompt_harness.core.logger import JsonlLogger

    p = tmp_path / "l.jsonl"
    lg = JsonlLogger(p, level="warning")  # canonical spelling must work
    lg.log("warning", "canonical_event", k=1)
    lg.log("warn", "alias_event", k=2)  # alias still accepted
    lg.log("info", "below_threshold", k=3)  # must be filtered

    lines = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()]
    events = [r["event"] for r in lines]
    assert "canonical_event" in events
    assert "alias_event" in events
    assert "below_threshold" not in events
