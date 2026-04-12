# Reference: CLI

dph is invoked as a Python module:

```
python -m dynamic_prompt_harness <trigger>
```

`<trigger>` is one of `pre_tool_use`, `post_tool_use`,
`user_prompt_submit`, `pre_compact`.

## Input

The raw Claude Code hook JSON is read from stdin. The active adapter
(currently `ClaudeCodeAdapter`) normalizes it into the abstract input
described in [subprocess-contract.md](subprocess-contract.md).

## Output

A single JSON object on stdout, shaped for Claude Code's hook response:

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow | deny",
    "permissionDecisionReason": "..."
  }
}
```

For `hint`-only composed results, dph emits Claude Code's additional-
context shape rather than a permission decision.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (the decision is in stdout) |
| non-zero | Never emitted intentionally — dph is fail-safe. A non-zero exit indicates a Python interpreter failure before dph could catch it |

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DPH_LOG_LEVEL` | `info` | One of `debug`, `info`, `warning`, `error` |
| `DPH_REGISTRY_PATH` | `.claude/dynamic-prompt-harness/registry.json` | Override the registry location (primarily for tests) |
| `DPH_LOG_PATH` | `.claude/dynamic-prompt-harness/logs/dph.log` | Override the log file location |

## Example

```bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' \
  | DPH_LOG_LEVEL=debug python -m dynamic_prompt_harness pre_tool_use
```
