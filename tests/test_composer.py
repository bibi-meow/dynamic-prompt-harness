from dynamic_prompt_harness.core.composer import Composer
from dynamic_prompt_harness.core.io_contract import AbstractResult, Decision

def _r(d, msg=None):
    return AbstractResult(decision=d, message=msg, metadata={})

def test_empty_means_allow():
    assert Composer().compose([]).decision is Decision.ALLOW

def test_all_allow():
    assert Composer().compose([_r(Decision.ALLOW), _r(Decision.ALLOW)]).decision is Decision.ALLOW

def test_any_deny_wins():
    out = Composer().compose([_r(Decision.ALLOW), _r(Decision.DENY, "no"), _r(Decision.HINT, "tip")])
    assert out.decision is Decision.DENY and "no" in (out.message or "")

def test_hint_accumulates():
    out = Composer().compose([_r(Decision.HINT, "a"), _r(Decision.HINT, "b")])
    assert out.decision is Decision.HINT
    assert "a" in out.message and "b" in out.message


def test_compose_preserves_per_entry_metadata_and_joins_messages():
    from dynamic_prompt_harness.core.composer import Composer
    from dynamic_prompt_harness.core.io_contract import (
        AbstractResult, Decision, Entry,
    )

    entries = [
        Entry(id="a", triggers=("pre_tool_use",), command=("x",),
              priority=0, timeout_sec=30.0, log_level=None, matcher=None),
        Entry(id="b", triggers=("pre_tool_use",), command=("y",),
              priority=0, timeout_sec=30.0, log_level=None, matcher=None),
        Entry(id="c", triggers=("pre_tool_use",), command=("z",),
              priority=0, timeout_sec=30.0, log_level=None, matcher=None),
    ]
    results = [
        AbstractResult(Decision.DENY, "policy_a_violation", {"rule": "A"}),
        AbstractResult(Decision.ALLOW, None, {}),
        AbstractResult(Decision.DENY, "policy_c_violation", {"rule": "C"}),
    ]

    merged = Composer().compose(results, entries)

    assert merged.decision is Decision.DENY
    assert merged.message == "policy_a_violation; policy_c_violation"
    assert merged.metadata == {
        "per_entry": {
            "a": {"rule": "A"},
            "b": {},
            "c": {"rule": "C"},
        }
    }
