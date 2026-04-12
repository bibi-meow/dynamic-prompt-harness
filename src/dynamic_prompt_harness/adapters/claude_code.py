import json
from ..core.io_contract import AbstractInput, AbstractResult, Decision
from ..core.errors import AdapterError

_TRIGGER_EVENT = {
    "pre_tool_use": "PreToolUse", "post_tool_use": "PostToolUse",
    "user_prompt_submit": "UserPromptSubmit", "pre_compact": "PreCompact",
}

class ClaudeCodeAdapter:
    def parse_input(self, raw: str, trigger: str) -> AbstractInput:
        try:
            d = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as e:
            raise AdapterError(f"invalid hook JSON: {e}") from e
        return AbstractInput(
            trigger=trigger,
            tool=d.get("tool_name"),
            tool_input=d.get("tool_input") or {},
            tool_result=d.get("tool_response"),
            prompt=d.get("prompt"),
            context={
                "session_id": d.get("session_id"),
                "cwd": d.get("cwd"),
                "transcript_path": d.get("transcript_path"),
                "hook_event_name": d.get("hook_event_name"),
            },
        )

    def format_output(self, result: AbstractResult, trigger: str) -> tuple[str, int]:
        if result.decision is Decision.ALLOW:
            return "", 0
        event = _TRIGGER_EVENT.get(trigger, "")
        if result.decision is Decision.DENY:
            if trigger in ("pre_tool_use",):
                payload = {"hookSpecificOutput": {
                    "hookEventName": event,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": result.message or "denied",
                }}
            elif trigger == "user_prompt_submit":
                payload = {"decision": "block", "reason": result.message or "blocked"}
            else:
                payload = {"decision": "block", "reason": result.message or "blocked"}
            return json.dumps(payload, ensure_ascii=False), 0
        # HINT
        if trigger == "user_prompt_submit":
            payload = {"hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": result.message or "",
            }}
        else:
            payload = {"hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": result.message or "",
            }}
        return json.dumps(payload, ensure_ascii=False), 0
