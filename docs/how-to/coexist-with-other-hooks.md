# How to coexist with existing Claude Code hooks

dph **does not replace** `.claude/settings.json` hooks. It sits next to
them and composes its own entries with AND semantics. This page explains
how they interact and how to migrate incrementally.

## Execution model

Claude Code calls every hook registered for an event. If you have:

- `.claude/settings.json` → a hook that runs `./scripts/safety.sh`
- `.claude/settings.json` → a hook that runs `python -m dynamic_prompt_harness pre_tool_use`

Both run. Claude Code then applies **AND** across their decisions: any
DENY vetoes the tool call. Internally dph does the same across its
registry entries.

So `settings.json` hooks and dph registry entries already compose
correctly. No special wiring is needed.

## Recommended wiring

Keep one hook per event that calls the dispatcher:

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": ".*", "hooks": [
        {"type": "command", "command": "python -m dynamic_prompt_harness pre_tool_use"}
      ]}
    ],
    "PostToolUse": [
      {"matcher": ".*", "hooks": [
        {"type": "command", "command": "python -m dynamic_prompt_harness post_tool_use"}
      ]}
    ],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness user_prompt_submit"}]}
    ],
    "PreCompact": [
      {"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_compact"}]}
    ]
  }
}
```

Move individual rules into registry entries over time.

## Migration path

For each legacy hook script:

1. Identify the trigger it listens to and the tools it matches.
2. Convert its stdin parsing to the dph input schema (see
   [reference/subprocess-contract.md](../reference/subprocess-contract.md)).
3. Add an entry to `registry.json` with its `command`, `triggers`, and
   `matcher`.
4. Remove the direct hook entry from `settings.json`.
5. Run `python -m pytest` (if you have tests) and smoke-test end-to-end.

## Ordering

dph runs higher-`priority` entries first. Claude Code runs
`settings.json` hooks in declaration order. If you need strict ordering
across layers, put everything inside the registry.

## Debugging interaction issues

- Set `DPH_LOG_LEVEL=debug` to see which entries matched and what they
  returned.
- Check `.claude/dynamic-prompt-harness/logs/dph.log` — every decision
  is logged as JSONL.
- See [troubleshoot.md](troubleshoot.md) for common failures.
