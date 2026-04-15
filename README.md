# dynamic-prompt-harness (dph)

A registry-driven hook dispatcher for Claude Code (and, eventually, other coding agents): declare small, composable rules in JSON; dph runs them as subprocesses and merges their verdicts with a safe AND-composition.

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![tests](https://img.shields.io/badge/tests-36%20passing-brightgreen)

## Why

Modern coding agents are powerful but non-deterministic. A thin **deterministic harness** around the agent — a place to encode hard rules ("never `rm -rf /`", "never commit `.env`", "log every Bash call") — complements the LLM's flexibility without fighting it. dph makes that harness **composable**: instead of one ever-growing hook script, you register many small rules. Any rule can veto a tool call, all rules see the same input, and a broken rule can never brick your agent (fail-safe ALLOW). The core is vendor-neutral; Claude Code is the first adapter.

## Quickstart

Install as a Claude Code plugin via the community marketplace:

```
/plugin marketplace add bibi-meow/dynamic-prompt-harness
/plugin install dynamic-prompt-harness@dynamic-prompt-harness
/reload-plugins
```

Then create an empty registry in your project root so dph has something to load:

```bash
mkdir -p .claude/dynamic-prompt-harness
cat > .claude/dynamic-prompt-harness/registry.json <<'JSON'
{"version": 1, "entries": []}
JSON
```

Add entries to `registry.json` to activate rules. Walkthrough: [docs/tutorial/01-first-harness.md](docs/tutorial/01-first-harness.md).

### Developer install (from source)

```bash
git clone https://github.com/bibi-meow/dynamic-prompt-harness.git
cd dynamic-prompt-harness
pip install -e .
python -m pytest tests/ -v
```

## Documentation (Diátaxis)

| Quadrant | Link | When to read |
|---|---|---|
| Tutorial | [docs/tutorial/](docs/tutorial/) | You are new — learn by doing |
| How-to | [docs/how-to/](docs/how-to/) | You have a specific problem to solve |
| Reference | [docs/reference/](docs/reference/) | You need precise schema / contracts |
| Explanation | [docs/explanation/](docs/explanation/) | You want the "why" behind the design |

Engineering record (ASPICE-aligned): [docs/sys/](docs/sys/), [docs/swe/](docs/swe/).

## Registry (summary)

Place at `.claude/dynamic-prompt-harness/registry.json`. Schema v1:

- `version`: must be `1`
- `entries[]`:
  - `id` (str, required)
  - `triggers` (list of `pre_tool_use` | `post_tool_use` | `user_prompt_submit` | `pre_compact`, required)
  - `command` (list, required; argv for the subprocess)
  - `matcher` (regex on tool name, optional)
  - `priority` (int, default `0`; higher runs first)
  - `timeout_sec` (number, default `30.0`)

Full reference: [docs/reference/registry-schema.md](docs/reference/registry-schema.md).
If `registry.json` is absent, dph is fail-safe ALLOW.

## Subprocess contract (summary)

- **stdin**: JSON with `trigger`, `tool`, `tool_input`, `tool_result`, `prompt`, `context`
- **stdout**: JSON `{"decision": "allow" | "deny" | "hint", "message": "...", "metadata": {...}}`
- **exit 0 + empty stdout** = ALLOW; non-zero exit or timeout = DENY

Full reference: [docs/reference/subprocess-contract.md](docs/reference/subprocess-contract.md).

## Troubleshooting

- Enable debug logging: `DPH_LOG_LEVEL=debug`
- Log file (JSONL): `.claude/dynamic-prompt-harness/logs/dph.log`
- The dispatcher catches all exceptions and fails safe (ALLOW) so a broken entry cannot brick the agent — watch the log to spot silent failures.

More: [docs/how-to/troubleshoot.md](docs/how-to/troubleshoot.md).

### Known issue: VSCode native extension does not fire plugin hooks

Upstream bug [anthropics/claude-code#18547](https://github.com/anthropics/claude-code/issues/18547): the VSCode Claude Code extension registers plugin hooks on `/reload-plugins` but does not dispatch them on actual tool invocations. Confirmed on v2.1.92.

**Not affected**: Claude Code CLI (`claude` / `claude -p`). dph fires normally there.

**Workaround for VSCode users** — copy the hook commands from `hooks/hooks.json` into `~/.claude/settings.json` (or project `.claude/settings.json`) manually:

```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_tool_use"}]}],
    "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness post_tool_use"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness user_prompt_submit"}]}],
    "PreCompact": [{"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_compact"}]}]
  }
}
```

This loses plugin portability (hooks no longer update with the plugin) but restores firing until the upstream bug is fixed.

## Tests

```bash
python -m pytest tests/ -v
```

## License

MIT.
