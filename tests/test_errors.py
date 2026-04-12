from dynamic_prompt_harness.core.errors import (
    DPHError, RegistryError, ExecutionError, SchemaError, AdapterError,
)

def test_hierarchy():
    for cls in (RegistryError, ExecutionError, SchemaError, AdapterError):
        assert issubclass(cls, DPHError)

def test_fields():
    e = DPHError("boom", code="X1", detail={"k": "v"})
    assert e.code == "X1" and e.detail == {"k": "v"}
