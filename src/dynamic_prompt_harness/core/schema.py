import re
from .errors import SchemaError

VALID_TRIGGERS = {"pre_tool_use", "post_tool_use", "user_prompt_submit", "pre_compact"}
VALID_LOG_LEVELS = {"debug", "info", "warning", "warn", "error"}

class SchemaValidator:
    def validate(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise SchemaError("root must be object")
        if data.get("version") != 1:
            raise SchemaError("version must be 1", code="E_VERSION")
        entries = data.get("entries")
        if not isinstance(entries, list):
            raise SchemaError("entries must be list")

        seen_ids: set[str] = set()
        for i, e in enumerate(entries):
            self._validate_entry(i, e)
            eid = e["id"]
            if eid in seen_ids:
                raise SchemaError(
                    f"entry[{i}].id duplicate: {eid!r}",
                    code="E_DUPLICATE_ID",
                    detail={"id": eid, "index": i},
                )
            seen_ids.add(eid)

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
            raise SchemaError(
                f"entry[{idx}].command must be non-empty list",
                code="E_BAD_COMMAND",
            )
        for j, part in enumerate(cmd):
            if not isinstance(part, str):
                raise SchemaError(
                    f"entry[{idx}].command[{j}] must be string (got {type(part).__name__})",
                    code="E_BAD_COMMAND",
                )

        if "priority" in e and not isinstance(e["priority"], int):
            raise SchemaError(f"entry[{idx}].priority must be int")

        if "timeout_sec" in e:
            ts = e["timeout_sec"]
            if not isinstance(ts, (int, float)) or isinstance(ts, bool):
                raise SchemaError(
                    f"entry[{idx}].timeout_sec must be number",
                    code="E_BAD_TIMEOUT",
                )
            if ts <= 0:
                raise SchemaError(
                    f"entry[{idx}].timeout_sec must be > 0 (got {ts})",
                    code="E_BAD_TIMEOUT",
                )

        if "log_level" in e and e["log_level"] is not None:
            ll = e["log_level"]
            if ll not in VALID_LOG_LEVELS:
                raise SchemaError(
                    f"entry[{idx}].log_level unknown: {ll!r}",
                    code="E_BAD_LOG_LEVEL",
                )

        if "matcher" in e and e["matcher"] is not None:
            m = e["matcher"]
            if not isinstance(m, str):
                raise SchemaError(
                    f"entry[{idx}].matcher must be string",
                    code="E_BAD_MATCHER",
                )
            try:
                re.compile(m)
            except re.error as re_err:
                raise SchemaError(
                    f"entry[{idx}].matcher invalid regex: {re_err}",
                    code="E_BAD_MATCHER",
                    detail={"matcher": m},
                ) from re_err
