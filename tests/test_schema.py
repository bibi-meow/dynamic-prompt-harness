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
