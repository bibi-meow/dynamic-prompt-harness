import sys

from dynamic_prompt_harness.core.executor import Executor
from dynamic_prompt_harness.core.io_contract import AbstractInput, Decision, Entry
from dynamic_prompt_harness.core.logger import JsonlLogger


def _entry(cmd, timeout=5.0):
    return Entry(
        id="t",
        triggers=("pre_tool_use",),
        command=tuple(cmd),
        priority=0,
        timeout_sec=timeout,
        log_level=None,
        matcher=None,
    )


def _input():
    return AbstractInput("pre_tool_use", "Write", {"file_path": "/x"}, None, None, {})


def test_exit0_stdout_decision(tmp_path):
    code = 'import json,sys; json.dump({"decision":"allow"}, sys.stdout)'
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(_entry([sys.executable, "-c", code]), _input())
    assert r.decision is Decision.ALLOW


def test_deny_via_stdout(tmp_path):
    code = 'import json,sys; json.dump({"decision":"deny","message":"nope"}, sys.stdout)'
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(_entry([sys.executable, "-c", code]), _input())
    assert r.decision is Decision.DENY and r.message == "nope"


def test_nonzero_exit_is_deny(tmp_path):
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(_entry([sys.executable, "-c", "import sys; sys.exit(2)"]), _input())
    assert r.decision is Decision.DENY


def test_timeout_is_deny(tmp_path):
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(
        _entry([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.3),
        _input(),
    )
    assert r.decision is Decision.DENY


def test_invalid_json_stdout_is_deny(tmp_path):
    code = 'import sys; sys.stdout.write("not json")'
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(_entry([sys.executable, "-c", code]), _input())
    assert r.decision is Decision.DENY
    assert r.metadata.get("reason") == "unparseable_stdout"


def test_entry_env_vars_exposed(tmp_path):
    code = (
        "import os,json,sys;"
        'json.dump({"decision":"hint","message":'
        'os.environ["DPH_ENTRY_ID"]+"/"+os.environ["DPH_TRIGGER"]}, sys.stdout)'
    )
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(_entry([sys.executable, "-c", code]), _input())
    assert r.decision is Decision.HINT
    assert r.message == "t/pre_tool_use"


def test_empty_stdout_exit0_is_allow(tmp_path):
    ex = Executor(tmp_path, JsonlLogger(tmp_path / "l.log"))
    r = ex.execute(_entry([sys.executable, "-c", ""]), _input())
    assert r.decision is Decision.ALLOW
