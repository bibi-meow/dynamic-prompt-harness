# Reference: Triggers

dph supports the four Claude Code hook events that matter for safety
and observability. Each maps to a dispatcher subcommand:

```
python -m dynamic_prompt_harness <trigger>
```

| Trigger (dph) | Claude Code event | Typical use |
|---|---|---|
| `pre_tool_use` | `PreToolUse` | Block/allow a tool call before it runs |
| `post_tool_use` | `PostToolUse` | Observe results, emit telemetry, react to failure |
| `user_prompt_submit` | `UserPromptSubmit` | Inspect/annotate the user's prompt before the agent sees it |
| `pre_compact` | `PreCompact` | Guard conversation compaction (e.g. require a diary entry first) |

## Stdin payload per trigger

All triggers share this shape after normalization by the adapter:

```json
{
  "trigger": "<trigger>",
  "tool": "<tool name or null>",
  "tool_input": { /* tool-specific or null */ },
  "tool_result": { /* post_tool_use only; adapter maps Claude Code's `tool_response` field to this key */ },
  "prompt": "<user prompt or null>",
  "context": {
    "session_id": "...",
    "cwd": "...",
    "transcript_path": "...",
    "hook_event_name": "..."
  }
}
```

Per trigger:

| Trigger | `tool` | `tool_input` | `tool_result` | `prompt` |
|---|---|---|---|---|
| `pre_tool_use` | set | set | `null` | `null` |
| `post_tool_use` | set | set | set | `null` |
| `user_prompt_submit` | `null` | `null` | `null` | set |
| `pre_compact` | `null` | `null` | `null` | `null` |

## When Claude Code calls them

- **PreToolUse** — after the model has chosen a tool call, before
  execution. DENY prevents the call.
- **PostToolUse** — after execution, before the result is returned to
  the model. DENY here cannot undo side effects; use for logging and
  alerting.
- **UserPromptSubmit** — after the user hits enter, before the prompt
  reaches the model. DENY suppresses the prompt.
- **PreCompact** — before `/compact`. DENY blocks compaction.

## Matchers

Only `pre_tool_use` and `post_tool_use` have a `tool` field, so the
`matcher` regex applies to those triggers. For `user_prompt_submit` and
`pre_compact`, `matcher` is ignored.
