# Tutorial: Your first harness in 15 minutes

By the end, you will have a working dph harness that **blocks `rm -rf /`**
before Claude Code can execute it, and you will have seen the decision
logged to `dph.log`.

The steps are copy-paste runnable on Linux, macOS, and Windows (Git Bash).

## 1. Install dph

From a clone of this repository:

```bash
pip install -e .
```

Verify (empty stdin + no registry = fail-safe ALLOW, empty output, exit 0):

```bash
echo '{}' | python -m dynamic_prompt_harness pre_tool_use ; echo "exit=$?"
```

## 2. Create the registry

dph reads its rules from `.claude/dynamic-prompt-harness/registry.json`
in the project you are running Claude Code against. Create it:

```bash
mkdir -p .claude/dynamic-prompt-harness
cat > .claude/dynamic-prompt-harness/registry.json <<'JSON'
{
  "version": 1,
  "entries": [
    {
      "id": "block-rm-rf-root",
      "triggers": ["pre_tool_use"],
      "matcher": "^Bash$",
      "command": ["python", ".claude/dynamic-prompt-harness/block_rm_rf.py"],
      "priority": 100,
      "timeout_sec": 5.0
    }
  ]
}
JSON
```

## 3. Write the harness (10 lines of Python)

```bash
cat > .claude/dynamic-prompt-harness/block_rm_rf.py <<'PY'
import json, sys
payload = json.load(sys.stdin)
cmd = (payload.get("tool_input") or {}).get("command", "")
if "rm -rf /" in cmd or "rm -rf /*" in cmd:
    print(json.dumps({"decision": "deny", "message": "refused: rm -rf / is blocked by dph"}))
    sys.exit(0)
# Empty stdout + exit 0 = ALLOW
PY
```

## 4. Wire the Claude Code hook

If you are using dph as a Claude Code plugin, `hooks/hooks.json` already
wires the dispatcher. Otherwise, add this to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_tool_use"}]}
    ]
  }
}
```

See [how-to/coexist-with-other-hooks.md](../how-to/coexist-with-other-hooks.md)
if you already have hooks configured.

## 5. Trigger it

Simulate the Claude Code hook invocation:

```bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' \
  | python -m dynamic_prompt_harness pre_tool_use
```

Expected output (shape):

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "refused: rm -rf / is blocked by dph"}}
```

## 6. Inspect the log

```bash
cat .claude/dynamic-prompt-harness/logs/dph.log
```

Each line is a JSON record: the resolved entries, the subprocess decision,
and the composed output. Use `DPH_LOG_LEVEL=debug` for more detail.

## What you learned

- Registry entries are **declarative JSON** — no Python for wiring.
- A harness is a **subprocess** that reads JSON from stdin and writes a
  `Decision` JSON to stdout.
- `exit 0` with empty stdout means ALLOW; a `deny` decision is a veto.
- dph **composes** multiple entries with AND semantics — any DENY wins.
- Everything is **logged** as JSONL; dph is fail-safe ALLOW if anything
  breaks.

Next: [how-to/add-custom-harness.md](../how-to/add-custom-harness.md) for
more harness patterns, or [reference/registry-schema.md](../reference/registry-schema.md)
for the full schema.
