# How to add a custom harness

A harness is any executable that honors the dph subprocess contract.
This page is a cookbook of minimal examples.

## The contract (one sentence)

Read a JSON object from stdin, write a JSON `Decision` to stdout (or
nothing), exit `0`. Full spec: [reference/subprocess-contract.md](../reference/subprocess-contract.md).

Input fields you receive on stdin:

- `trigger` — e.g. `"pre_tool_use"`
- `tool` — tool name (e.g. `"Bash"`) or `null`
- `tool_input` — object (tool-specific)
- `prompt` — user prompt string or `null`
- `context` — object with `session_id`, `cwd`, `transcript_path`, `hook_event_name`

Output: `{"decision": "allow" | "deny" | "hint", "message": "...", "metadata": {...}}`.
Empty stdout with exit 0 = ALLOW.

## Python

```python
#!/usr/bin/env python3
import json, sys
payload = json.load(sys.stdin)
if "secret" in (payload.get("tool_input") or {}).get("command", ""):
    print(json.dumps({"decision": "deny", "message": "contains 'secret'"}))
sys.exit(0)
```

Register:

```json
{"id": "no-secret", "triggers": ["pre_tool_use"], "matcher": "^Bash$",
 "command": ["python", ".claude/dynamic-prompt-harness/no_secret.py"]}
```

## Bash

Requires `jq` (pre-installed on macOS, Linux, and Git Bash via MSYS2):

```bash
#!/usr/bin/env bash
set -euo pipefail
cmd="$(jq -r '.tool_input.command // ""')"
case "$cmd" in
  *".env"*) printf '{"decision":"deny","message":"refused: .env touched"}\n' ;;
esac
```

Register with `"command": ["bash", ".claude/dynamic-prompt-harness/no_env.sh"]`.

## Node.js

```js
#!/usr/bin/env node
let data = "";
process.stdin.on("data", c => data += c);
process.stdin.on("end", () => {
  const p = JSON.parse(data);
  if ((p.prompt || "").match(/prod deploy/i)) {
    process.stdout.write(JSON.stringify({decision: "hint", message: "be careful with prod"}));
  }
});
```

Register with `"command": ["node", ".claude/dynamic-prompt-harness/prod_warn.js"]`.

## Tips

- Keep each harness small and single-purpose; compose via the registry.
- Prefer `hint` over `deny` when you want to surface context without
  blocking — dph passes hints to Claude Code as additional context.
- Set a tight `timeout_sec` (e.g. `2.0`) for hot-path rules.
- Put shared logic in a helper module and import it from multiple
  harnesses — each entry is just an argv.
