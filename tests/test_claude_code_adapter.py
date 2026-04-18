import json
from pathlib import Path

from dynamic_prompt_harness.adapters.claude_code import ClaudeCodeAdapter
from dynamic_prompt_harness.core.io_contract import AbstractResult, Decision

FX = Path(__file__).parent / "fixtures"


def test_parse_pre_tool_use():
    raw = (FX / "pre_tool_use_write.json").read_text(encoding="utf-8")
    inp = ClaudeCodeAdapter().parse_input(raw, "pre_tool_use")
    assert inp.trigger == "pre_tool_use" and inp.tool == "Write"
    assert inp.tool_input["file_path"] == "/x"


def test_parse_user_prompt_submit():
    raw = (FX / "user_prompt_submit.json").read_text(encoding="utf-8")
    inp = ClaudeCodeAdapter().parse_input(raw, "user_prompt_submit")
    assert inp.prompt == "hello" and inp.tool is None


def test_format_allow_is_exit0_empty():
    out, rc = ClaudeCodeAdapter().format_output(
        AbstractResult(Decision.ALLOW, None, {}), "pre_tool_use"
    )
    assert rc == 0 and out == ""


def test_format_deny_pretooluse_uses_json_decision():
    out, rc = ClaudeCodeAdapter().format_output(
        AbstractResult(Decision.DENY, "nope", {}), "pre_tool_use"
    )
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "nope" in payload["hookSpecificOutput"]["permissionDecisionReason"]
    assert rc == 0


def test_format_hint_on_user_prompt_submit_uses_additional_context():
    out, rc = ClaudeCodeAdapter().format_output(
        AbstractResult(Decision.HINT, "reminder", {}), "user_prompt_submit"
    )
    payload = json.loads(out)
    assert "reminder" in payload["hookSpecificOutput"]["additionalContext"]
    assert rc == 0
