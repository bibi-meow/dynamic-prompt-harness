# Reference: Subprocess Contract

Every registry entry is invoked as a subprocess. This document is the
formal I/O contract between dph and a harness.

## Invocation

dph spawns `command[0] command[1:]...` with:

- `stdin`: a single JSON object (see below), followed by EOF
- `stdout`: captured in full
- `stderr`: captured and logged (not inspected for decisions)
- `cwd`: the agent's working directory (from `context.cwd`)
- `env`: inherited from dph, plus `DPH_ENTRY_ID=<entry.id>`,
  `DPH_TRIGGER=<trigger>`, and (if set on the entry) `DPH_LOG_LEVEL=<entry.log_level>`
- `timeout`: `entry.timeout_sec` seconds

## Stdin schema

```json
{
  "trigger": "pre_tool_use | post_tool_use | user_prompt_submit | pre_compact",
  "tool": "string | null",
  "tool_input": "object | null",
  "tool_result": "object | null",
  "prompt": "string | null",
  "context": {
    "session_id": "string",
    "cwd": "string",
    "transcript_path": "string",
    "hook_event_name": "string"
  }
}
```

See [triggers.md](triggers.md) for which fields are populated per trigger.

## Stdout schema (Decision)

```json
{
  "decision": "allow" | "deny" | "hint",
  "message": "string (optional, recommended for deny/hint)",
  "metadata": { /* optional, free-form; surfaced to the log */ }
}
```

- `allow` — no opinion; ALLOW with no message.
- `deny` — veto. Claude Code blocks the tool call (or prompt / compact).
  `message` is shown to the user and model.
- `hint` — advisory. Not a veto; `message` is surfaced to the model as
  additional context.

### Shortcut: empty stdout

If stdout is empty and exit code is 0, dph treats the result as
`{"decision": "allow"}`. This is the recommended default for "no
opinion" rules — it costs less than constructing JSON.

## Exit code semantics

| Exit code | Stdout | Result |
|---|---|---|
| `0` | empty | ALLOW |
| `0` | valid Decision JSON | that Decision |
| `0` | non-empty, invalid JSON | DENY (logged as `invalid decision JSON`) |
| non-zero | any | DENY (logged as `subprocess nonzero exit`) |
| (timeout) | any | DENY (logged as `subprocess timeout`) |

Rationale: a safety rule that fails to report should not be silently
skipped. Per-entry fail-closed. **Dispatcher-level** failures (dph
itself crashing) are fail-open ALLOW — a broken dph must not brick the
agent.

## Composition

dph runs all matching entries (ordered by `priority` desc) and applies
AND-composition:

- Any `deny` → final decision is DENY (deny messages concatenated).
- Otherwise, any `hint` → final decision is HINT (hint messages
  concatenated).
- Otherwise → ALLOW.
