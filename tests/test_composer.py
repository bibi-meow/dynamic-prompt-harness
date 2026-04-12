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
