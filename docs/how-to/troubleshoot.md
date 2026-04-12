# Troubleshooting

## Quick checks

1. Is `registry.json` at `.claude/dynamic-prompt-harness/registry.json`?
   If missing, dph is fail-safe ALLOW (and logs nothing).
2. Is `DPH_LOG_LEVEL=debug` set? Without it, only warnings and errors
   are logged.
3. Does `.claude/dynamic-prompt-harness/logs/dph.log` exist and contain
   recent entries? Tail it while reproducing.

## Log location

`.claude/dynamic-prompt-harness/logs/dph.log` (JSONL, one decision per
line). Each record includes the trigger, matched entries, subprocess
exit codes, stdout, composed decision, and timing.

## Log levels

Set via `DPH_LOG_LEVEL` environment variable:

| Value | Records |
|---|---|
| `debug` | Every decision, every entry resolution, every subprocess call |
| `info` (default) | Decisions and errors |
| `warning` | Unexpected subprocess behavior only |
| `error` | Failures only |

## Common errors

### "registry not found"

Not an error — dph logs this at `debug` and exits ALLOW. Create the
file if you intended to load rules.

### "schema error: ..."

Your `registry.json` violates schema v1. See
[reference/registry-schema.md](../reference/registry-schema.md).
Typical causes:

- `version` missing or not `1`
- `triggers` contains an unknown value
- `command` is a string rather than a list

Fix the registry; dph fail-safes to ALLOW while broken.

### "subprocess timeout"

The entry's `command` exceeded `timeout_sec`. dph treats this as DENY
(fail-closed per entry, because an unresponsive safety rule should not
be silently skipped). Either optimize the harness or raise
`timeout_sec`.

### "subprocess nonzero exit"

Same as timeout: treated as DENY. Check the log record — stdout and
stderr are captured — and fix the harness.

### "invalid decision JSON"

The harness wrote something that was not an empty string and not a
valid `Decision` object. Treated as DENY. Fix the harness's output.

## Reading `dph.log`

Each line is one JSON object. Useful fields:

- `trigger` — which trigger fired
- `tool` — tool name
- `entries` — list of resolved entries with per-entry decision
- `composed` — the final decision after AND-composition
- `duration_ms` — total dispatcher time

Filter with jq:

```bash
jq 'select(.composed.decision == "deny")' .claude/dynamic-prompt-harness/logs/dph.log
```

## Dispatcher is fail-safe

If dph itself raises an unexpected exception, it catches the exception,
logs it at `error`, and exits ALLOW (empty stdout, exit 0). A broken
dph installation cannot brick your agent. The trade-off: a silent dph
is a disabled dph — keep an eye on the log.
