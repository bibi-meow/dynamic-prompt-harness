import pytest
from dynamic_prompt_harness.core.schema import SchemaValidator
from dynamic_prompt_harness.core.errors import SchemaError

VALID = {"version": 1, "entries": [
    {"id": "a", "triggers": ["pre_tool_use"], "command": ["echo", "hi"]}
]}

def test_valid():
    SchemaValidator().validate(VALID)

def test_missing_version():
    with pytest.raises(SchemaError):
        SchemaValidator().validate({"entries": []})

def test_entry_missing_id():
    bad = {"version": 1, "entries": [{"triggers": ["pre_tool_use"], "command": ["x"]}]}
    with pytest.raises(SchemaError):
        SchemaValidator().validate(bad)

def test_invalid_trigger():
    bad = {"version": 1, "entries": [
        {"id": "a", "triggers": ["bogus"], "command": ["x"]}]}
    with pytest.raises(SchemaError):
        SchemaValidator().validate(bad)


def _entry(**overrides):
    base = {
        "id": "e1",
        "triggers": ["pre_tool_use"],
        "command": ["echo", "hi"],
    }
    base.update(overrides)
    return base


def test_schema_rejects_duplicate_ids():
    data = {"version": 1, "entries": [_entry(id="dup"), _entry(id="dup")]}
    with pytest.raises(SchemaError) as exc:
        SchemaValidator().validate(data)
    assert exc.value.code == "E_DUPLICATE_ID"


def test_schema_rejects_nonpositive_timeout():
    data = {"version": 1, "entries": [_entry(timeout_sec=0)]}
    with pytest.raises(SchemaError) as exc:
        SchemaValidator().validate(data)
    assert exc.value.code == "E_BAD_TIMEOUT"


def test_schema_rejects_negative_timeout():
    data = {"version": 1, "entries": [_entry(timeout_sec=-1)]}
    with pytest.raises(SchemaError) as exc:
        SchemaValidator().validate(data)
    assert exc.value.code == "E_BAD_TIMEOUT"


def test_schema_rejects_unknown_log_level():
    data = {"version": 1, "entries": [_entry(log_level="verbose")]}
    with pytest.raises(SchemaError) as exc:
        SchemaValidator().validate(data)
    assert exc.value.code == "E_BAD_LOG_LEVEL"


def test_schema_accepts_warn_alias_log_level():
    data = {"version": 1, "entries": [_entry(log_level="warn")]}
    SchemaValidator().validate(data)  # must not raise


def test_schema_accepts_warning_log_level():
    data = {"version": 1, "entries": [_entry(log_level="warning")]}
    SchemaValidator().validate(data)  # must not raise


def test_schema_rejects_non_string_command_element():
    data = {"version": 1, "entries": [_entry(command=["echo", 42])]}
    with pytest.raises(SchemaError) as exc:
        SchemaValidator().validate(data)
    assert exc.value.code == "E_BAD_COMMAND"


def test_schema_rejects_invalid_matcher_regex():
    data = {"version": 1, "entries": [_entry(matcher="(unclosed")]}
    with pytest.raises(SchemaError) as exc:
        SchemaValidator().validate(data)
    assert exc.value.code == "E_BAD_MATCHER"


def test_schema_accepts_valid_matcher_regex():
    data = {"version": 1, "entries": [_entry(matcher="^Bash$")]}
    SchemaValidator().validate(data)  # must not raise
