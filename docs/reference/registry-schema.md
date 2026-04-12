# Reference: Registry Schema v1

**Location:** `.claude/dynamic-prompt-harness/registry.json`
**Encoding:** UTF-8 JSON.
**Absent file:** dph fail-safes to ALLOW (no rules loaded).

## Top-level

```json
{
  "version": 1,
  "entries": [ /* Entry */ ]
}
```

| Field | Type | Required | Constraint |
|---|---|---|---|
| `version` | integer | yes | Must equal `1` |
| `entries` | array of Entry | yes | May be empty |

## Entry

```json
{
  "id": "block-rm-rf-root",
  "triggers": ["pre_tool_use"],
  "command": ["python", ".claude/dynamic-prompt-harness/block_rm_rf.py"],
  "matcher": "^Bash$",
  "priority": 100,
  "timeout_sec": 5.0,
  "log_level": "info"
}
```

| Field | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `id` | string | yes | — | Non-empty, unique across entries |
| `triggers` | array of string | yes | — | Each ∈ { `pre_tool_use`, `post_tool_use`, `user_prompt_submit`, `pre_compact` } |
| `command` | array of string | yes | — | argv passed to the subprocess; first element must be an executable resolvable on `PATH` or an absolute/relative path |
| `matcher` | string | no | `".*"` | Python regex matched against the tool name. Ignored for triggers that carry no tool (`user_prompt_submit`, `pre_compact`) |
| `priority` | integer | no | `0` | Higher runs first. Ties broken by registry order |
| `timeout_sec` | number | no | `30.0` | Must be > 0. Exceeding it yields DENY for that entry |
| `log_level` | string | no | inherits global | One of `debug`, `info`, `warn`, `error`. Passed to the harness subprocess as `DPH_LOG_LEVEL` |

## Example

```json
{
  "version": 1,
  "entries": [
    {
      "id": "block-rm-rf-root",
      "triggers": ["pre_tool_use"],
      "matcher": "^Bash$",
      "command": ["python", ".claude/dynamic-prompt-harness/block_rm_rf.py"],
      "priority": 100,
      "timeout_sec": 2.0
    },
    {
      "id": "warn-prod-deploy",
      "triggers": ["user_prompt_submit"],
      "command": ["node", ".claude/dynamic-prompt-harness/prod_warn.js"]
    }
  ]
}
```

## Validation errors

Invalid registries produce a `SchemaError` logged at `error` and dph
exits ALLOW. Fix the registry and rerun — no restart is required.

See also: [triggers.md](triggers.md), [subprocess-contract.md](subprocess-contract.md).
