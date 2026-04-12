import pytest
from dynamic_prompt_harness.core.io_contract import (
    AbstractInput, AbstractResult, Entry, Decision,
)

def test_decision_enum():
    assert Decision.ALLOW.value == "allow"
    assert Decision.DENY.value == "deny"
    assert Decision.HINT.value == "hint"

def test_entry_frozen():
    e = Entry(id="x", triggers=("pre_tool_use",), command=("echo", "hi"),
              priority=0, timeout_sec=30.0, log_level=None, matcher=None)
    with pytest.raises(Exception):
        e.priority = 1  # type: ignore

def test_abstract_input_defaults():
    i = AbstractInput(trigger="pre_tool_use", tool=None, tool_input={},
                      tool_result=None, prompt=None, context={})
    assert i.trigger == "pre_tool_use"

def test_abstract_result():
    r = AbstractResult(decision=Decision.ALLOW, message=None, metadata={})
    assert r.decision is Decision.ALLOW
