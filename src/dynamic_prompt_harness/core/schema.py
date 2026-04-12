from .errors import SchemaError

VALID_TRIGGERS = {"pre_tool_use", "post_tool_use", "user_prompt_submit", "pre_compact"}

class SchemaValidator:
    def validate(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise SchemaError("root must be object")
        if data.get("version") != 1:
            raise SchemaError("version must be 1", code="E_VERSION")
        entries = data.get("entries")
        if not isinstance(entries, list):
            raise SchemaError("entries must be list")
        for i, e in enumerate(entries):
            self._validate_entry(i, e)

    def _validate_entry(self, idx: int, e: dict) -> None:
        if not isinstance(e, dict):
            raise SchemaError(f"entry[{idx}] must be object")
        for key in ("id", "triggers", "command"):
            if key not in e:
                raise SchemaError(f"entry[{idx}] missing {key}")
        if not isinstance(e["id"], str) or not e["id"]:
            raise SchemaError(f"entry[{idx}].id invalid")
        trigs = e["triggers"]
        if not isinstance(trigs, list) or not trigs:
            raise SchemaError(f"entry[{idx}].triggers must be non-empty list")
        for t in trigs:
            if t not in VALID_TRIGGERS:
                raise SchemaError(f"entry[{idx}].triggers has unknown '{t}'")
        cmd = e["command"]
        if not isinstance(cmd, list) or not cmd:
            raise SchemaError(f"entry[{idx}].command must be non-empty list")
        if "priority" in e and not isinstance(e["priority"], int):
            raise SchemaError(f"entry[{idx}].priority must be int")
        if "timeout_sec" in e and not isinstance(e["timeout_sec"], (int, float)):
            raise SchemaError(f"entry[{idx}].timeout_sec must be number")
