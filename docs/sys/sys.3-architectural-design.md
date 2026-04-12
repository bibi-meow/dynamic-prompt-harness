# SYS.3 System Architectural Design: dynamic-prompt-harness

Architecture satisfying the FR/NFR/IR/CON defined in SYS.2 (system-requirements).
v0.1 scope. Described along 4 axes: module structure / data flow / interfaces / deployment.

## 1. Architectural Principles

| ID | Principle | Rationale |
|---|---|---|
| AP-1 | Keep the 3-layer separation (adapter / core / harness) enforced at the physical directory level | NFR-M-001 |
| AP-2 | `core` does not import `adapters`. One-way dependency: adapters reference core dataclasses | NFR-M-002 |
| AP-3 | harness connects to core across a subprocess boundary. No in-process references | FR-030 to 033 |
| AP-4 | dispatcher spawns a new process per hook invocation. Stateless | CON-001, §1.7 |
| AP-5 | registry load narrows by trigger first, then schema validate + filter | NFR-P-001 |
| AP-6 | Vendor-specific names are normalized inside the adapter; core/harness receive abstract names | NFR-PT-003 |

## 2. Module Structure

### 2.1 Repository / plugin layout

```
dynamic-prompt-harness/                   # repo root = plugin root
├── .claude-plugin/
│   └── plugin.json                       # IR-006 plugin manifest
├── hooks/
│   └── hooks.json                        # IR-007 PreToolUse/PostToolUse/
│                                         #        UserPromptSubmit/PreCompact → dispatcher
├── src/dynamic_prompt_harness/
│   ├── __init__.py
│   ├── __main__.py                       # entry point for python -m dynamic_prompt_harness
│   ├── dispatcher.py                     # orchestration (see 3.x below)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── registry.py                   # load + JSON Schema validate + trigger/tool/pattern filter
│   │   ├── executor.py                   # execution of declarative / script
│   │   ├── composer.py                   # priority sort + DENY short-circuit + hint concatenation
│   │   ├── io_contract.py                # AbstractInput / AbstractResult dataclass
│   │   ├── schema.py                     # registry.json JSON Schema definition
│   │   └── logger.py                     # JSONL logger + log_level
│   └── adapters/
│       ├── __init__.py                   # default adapter selection (fixed to claude_code in v0.1)
│       └── claude_code.py                # the 2 functions: parse_input / format_output
├── docs/sys/                             # SYS.1 / SYS.2 / SYS.3
└── README.md
```

### 2.2 User data layout (on the target project side)

```
<project>/.claude/dynamic-prompt-harness/
├── registry.json                         # IR-005
├── harnesses/                            # only script type is placed here
│   └── <name>.<arbitrary extension>
└── logs/
    └── dispatcher.jsonl                  # NFR-O-001
```

### 2.3 Dependency direction

```
hooks/hooks.json  ──▶  dispatcher.py
                          │
                          ├──▶  adapters.claude_code   (parse_input / format_output)
                          │          │
                          │          └──▶  core.io_contract (references dataclass only)
                          │
                          └──▶  core.{registry, executor, composer, logger}
                                       │
                                       └──▶  subprocess ──▶  <harness script>
```

There is no arrow from `core` to `adapters` (AP-2).

## 3. Dispatcher Design

### 3.1 Entry point

- Launched from a Claude Code hook via `python -m dynamic_prompt_harness <trigger>` (CON-003)
- `<trigger>` is one of `pre_tool_use` / `post_tool_use` / `user_prompt_submit` / `pre_compact`
- stdin receives Claude Code hook JSON; stdout emits hook output JSON

Rationale for invoking Python directly: interposing a bash wrapper would split the OS-difference absorption point into two places (sh/bat).
Unifying on Python lets us handle Windows / Linux / macOS on a single path (NFR-PT-001).

### 3.2 Processing sequence

```
1. __main__ reads sys.argv[1] = trigger
2. adapter.parse_input(stdin_json) → AbstractInput
      - Normalize vendor-specific keys (e.g. hookSpecificOutput)
      - Store session_id, cwd, transcript_path, hook_event_name into context (FR-031, FR-031a)
3. registry.load(trigger)
      - Load all registry.json entries → JSON Schema validate (FR-020)
      - Return only entries whose triggers contain <trigger> (primary narrowing, NFR-P-001)
4. registry.filter(entries, AbstractInput)
      - Secondary narrowing by tools / pattern (FR-012)
5. composer.sort(filtered)
      - Ascending by priority → ties broken by registry order (FR-013)
6. for entry in sorted:
      result = executor.run(entry, AbstractInput)
      results.append(result)
      logger.log(entry, result)
      if result.decision == DENY: break   # short-circuit (FR-014)
7. final = composer.merge(results)
      - If any DENY exists, DENY (first-win; already short-circuited)
      - Otherwise concatenate all hints (FR-015)
      - If none apply, ALLOW
8. adapter.format_output(final) → stdout JSON
```

### 3.3 Error policy

| Event | Behavior | Rationale |
|---|---|---|
| registry.json missing / corrupt | Log error to stderr, emit ALLOW on stdout and exit (fail-open) | NFR-R-002 |
| Non-zero exit / invalid JSON from an individual harness | Skip that result, log it, continue with the rest | FR-016, FR-017 |
| Harness hangs | dispatcher only waits; delegate to the Claude Code hook timeout | FR-016 |
| JSON parse failure in adapter | Write to stderr, exit with ALLOW | NFR-R-002 |

## 4. Core Module Details

### 4.1 `core.io_contract`

Defines the abstracted I/O as dataclasses. JSON ↔ dataclass conversion is confined here.

```python
@dataclass(frozen=True)
class AbstractInput:
    trigger: str            # "pre_tool_use" | "post_tool_use" | "user_prompt_submit" | "pre_compact"
    tool: str | None        # only for PreToolUse/PostToolUse
    tool_input: dict        # tool arguments (non-empty only for PreToolUse/PostToolUse)
    prompt: str | None      # only for UserPromptSubmit
    context: dict           # session_id, cwd, transcript_path, hook_event_name, ...

@dataclass(frozen=True)
class AbstractResult:
    decision: str           # "allow" | "deny" | "hint"
    message: str | None
    metadata: dict          # used to map to vendor-specific extensions (FR-041)
```

### 4.2 `core.registry`

```python
def load(trigger: str, registry_path: Path) -> list[Entry]:
    """Return only the enabled entries that match the trigger"""

def filter(entries: list[Entry], inp: AbstractInput) -> list[Entry]:
    """Secondary narrowing by tools / pattern"""
```

- `Entry` is a dataclass representing a single row of registry.json
- `script` / `action` must be mutually exclusive (validated by schema and also asserted at dataclass construction)
- Handled as `list[Entry]` to preserve registration order (not converted to a dict)

### 4.3 `core.executor`

```python
def run(entry: Entry, inp: AbstractInput) -> AbstractResult:
    if entry.action is not None:
        return _run_declarative(entry, inp)
    else:
        return _run_script(entry, inp)
```

- `_run_declarative`: pattern match is already confirmed by registry.filter → map `entry.action` directly into an AbstractResult (no subprocess spawn, NFR-P-002)
- `_run_script`:
  - Launch the script under `harnesses/` via subprocess.run
  - stdin = AbstractInput JSON, stdout = AbstractResult JSON
  - Non-zero exit / JSON parse failure is converted into `AbstractResult(decision="allow", ..., metadata={"error": ...})` (= treated as skipped)
  - Paths are restricted to under `harnesses/` (`..` traversal rejected, NFR-S-002)

### 4.4 `core.composer`

```python
def sort(entries: list[Entry]) -> list[Entry]:
    """Ascending by priority; ties preserve input order (stable sort)"""

def merge(results: list[AbstractResult]) -> AbstractResult:
    """DENY first-win / concatenate all hints / ALLOW if none"""
```

### 4.5 `core.schema`

Holds the registry.json JSON Schema (Draft 2020-12) as a Python dict.
Referenced by `registry.load` at startup. To avoid external dependencies, reimplement a lightweight custom validator or
a `jsonschema`-equivalent using only the standard library (NFR-PT-002: stdlib only).

### 4.6 `core.logger`

JSONL append. One line = one harness execution event.

```json
{
  "ts": "2026-04-12T21:55:00+09:00",
  "session_id": "...",
  "trigger": "pre_tool_use",
  "harness": "block-env-file",
  "decision": "deny",
  "duration_ms": 12,
  "error": null
}
```

log_level precedence: `DPH_LOG_LEVEL` env var > `registry.json.log_level` > default `info` (FR-018).

## 5. Adapter Layer

### 5.1 `adapters.claude_code`

Exposes only 2 functions (no per-trigger methods per vendor — so multiple vendors can be handled uniformly):

```python
def parse_input(raw: dict, trigger: str) -> AbstractInput:
    """Claude Code hook JSON → AbstractInput"""

def format_output(result: AbstractResult, trigger: str) -> dict:
    """AbstractResult → Claude Code hook JSON"""
```

### 5.2 Normalization mapping (v0.1)

| Claude Code hook field | Destination in AbstractInput |
|---|---|
| `session_id` | `context.session_id` |
| `cwd` | `context.cwd` |
| `transcript_path` | `context.transcript_path` |
| `hook_event_name` | `context.hook_event_name` |
| `tool_name` | `tool` |
| `tool_input` | `tool_input` |
| `prompt` | `prompt` |
| `hookSpecificOutput` | `context.hook_specific_output` (snake_case normalized) |

Output side:

| AbstractResult | Claude Code hook JSON |
|---|---|
| `decision = "deny"` | `{"decision": "block", "reason": message}` |
| `decision = "hint"` | `{"hookSpecificOutput": {"additionalContext": message}}` etc., shaped appropriately per trigger |
| `decision = "allow"` | `{}` (empty object = pass through) |
| `metadata.*` | adapter maps to vendor-specific fields |

Because the final JSON shape per trigger depends on the Claude Code hook spec, the adapter holds an internal table of trigger → formatter. This is a vendor-specific implementation detail, invisible to the core layer.

### 5.3 Future vendor additions

Add an implementation under `adapters/<vendor>.py` with the same 2-function signature.
Dispatcher adapter selection reserves `DPH_ADAPTER` env var as a future extension point (in v0.1, claude_code is fixed, CON-002).

## 6. Interface Definitions

### 6.1 IR-005: registry.json schema

```json
{
  "log_level": "info",
  "entries": [
    {
      "name": "block-env-add",
      "triggers": ["pre_tool_use"],
      "tools": ["Bash"],
      "pattern": "git\\s+add\\s+.*\\.env",
      "priority": 10,
      "enabled": true,
      "action": {
        "on_match": "deny",
        "message": "git add on .env is forbidden; secrets may leak."
      }
    },
    {
      "name": "post-commit-push-hint",
      "triggers": ["post_tool_use"],
      "tools": ["Bash"],
      "pattern": "git\\s+commit",
      "priority": 50,
      "enabled": true,
      "script": "post-commit-push-hint.py"
    }
  ]
}
```

Mutual-exclusion constraint: each entry has exactly one of `action` or `script` (FR-021).

### 6.2 IR-003: abstracted input JSON (dispatcher → harness)

```json
{
  "trigger": "pre_tool_use",
  "tool": "Bash",
  "tool_input": { "command": "git add .env" },
  "prompt": null,
  "context": {
    "session_id": "abc123",
    "cwd": "/path/to/project",
    "transcript_path": "...",
    "hook_event_name": "PreToolUse"
  }
}
```

### 6.3 IR-004: abstracted output JSON (harness → dispatcher)

```json
{
  "decision": "deny",
  "message": "Adding .env files is forbidden",
  "metadata": {}
}
```

### 6.4 IR-006: plugin manifest

```json
{
  "name": "dynamic-prompt-harness",
  "version": "0.1.0",
  "description": "Hook-based dynamic prompt injection runtime",
  "author": "bibi-meow"
}
```

### 6.5 IR-007: hooks.json

```json
{
  "hooks": {
    "PreToolUse":       [{"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_tool_use"}]}],
    "PostToolUse":      [{"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness post_tool_use"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness user_prompt_submit"}]}],
    "PreCompact":       [{"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_compact"}]}]
  }
}
```

## 7. Overall Data Flow

```
Claude Code hook fires
        │
        ▼  stdin: vendor hook JSON
┌─────────────────────────────────────────────┐
│ python -m dynamic_prompt_harness <trigger>  │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ adapters.claude_code.parse_input     │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼  AbstractInput            │
│  ┌──────────────────────────────────────┐   │
│  │ core.registry.load(trigger)          │   │
│  │   → JSON Schema validate             │   │
│  │   → primary narrowing by trigger     │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼  list[Entry]              │
│  ┌──────────────────────────────────────┐   │
│  │ core.registry.filter(tools, pattern) │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼                           │
│  ┌──────────────────────────────────────┐   │
│  │ core.composer.sort (priority+order)  │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼                           │
│  ┌──────────────────────────────────────┐   │
│  │ for entry in sorted:                 │   │
│  │   core.executor.run(entry, input)    │──────┐ subprocess (script type only)
│  │   → AbstractResult                   │     ▼
│  │   logger.log(...)                    │   harness script
│  │   if DENY: break                     │   (stdin/stdout JSON)
│  └──────────────┬───────────────────────┘     │
│                 ▼  list[AbstractResult]   ◀───┘
│  ┌──────────────────────────────────────┐   │
│  │ core.composer.merge                  │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼  AbstractResult           │
│  ┌──────────────────────────────────────┐   │
│  │ adapters.claude_code.format_output   │   │
│  └──────────────┬───────────────────────┘   │
└─────────────────┼───────────────────────────┘
                  ▼  stdout: vendor hook JSON
           Received by Claude Code
```

## 8. Coexistence with Existing Hooks

dph runs as an independent process separate from other Claude Code hooks, and coexists under the following premises (FR-070 to 073, US-F1 to 4).

### 8.1 Coexistence model

- Claude Code launches every registered hook for a given trigger. The dph dispatcher is merely one of them
- The dph dispatcher does not read or write other hook settings in `settings.json`
- Because each hook is an independent process, stdout / exit code / exit 2 (block) do not interfere
- The final decision follows Claude Code's hook composition model (if any one blocks, block = AND composition)

### 8.2 Conflict patterns and handling

| # | Pattern | dph behavior |
|---|---|---|
| 1 | Both a user hook and dph are registered on the same trigger | Both run independently. AND composition |
| 2 | The same logic is duplicated in a user hook and in a dph harness | Double execution occurs. The migration guide recommends removing it from settings.json (FR-073) |
| 3 | Execution order between user hook and dph | dph's `priority` is scoped to dph only. External order depends on Claude Code (FR-072) |
| 4 | User hook exits 2 while dph returns a JSON decision | No interference since they are separate paths |
| 5 | Both user hook and dph issue block decisions on PreCompact | AND composition; both must pass |

### 8.3 Behavior with an empty registry

When `registry.json` `entries` is empty, or there are 0 entries matching the trigger,
the dispatcher does not spawn any subprocess, returns ALLOW on stdout, and exits 0 (FR-071).
It does not break existing functionality in the empty state immediately after introduction.

### 8.4 Migration guide (provided as docs)

1. Convert existing hook logic into registry entries one by one (action for declarative cases, script otherwise)
2. Verify operation under dph
3. Remove the corresponding hook line from `settings.json`
4. Confirm via logs that double execution has stopped

## 9. Next Steps

- Class design (finalize relationships and method signatures of dispatcher/registry/executor/composer/io_contract/adapter)
- Implement starting from `core.*` via TDD (zero external dependencies, so the standard library unittest is sufficient)
- For `adapters.claude_code`, prepare contract tests based on real hook JSON samples
- v0.1 release → register on the Claude Code plugin marketplace

## 10. Traceability (excerpt)

| FR/NFR | Realizing module |
|---|---|
| FR-010 to 018 | `dispatcher.py` + `core.logger` |
| FR-020 to 022 | `core.registry` + `core.schema` |
| FR-021a/b | `core.executor._run_declarative` / `_run_script` |
| FR-030 to 033 | `core.io_contract` + subprocess boundary |
| FR-040 to 042 | `adapters/claude_code.py` |
| FR-050 to 055 | registry entry representation + executor's 2 paths |
| NFR-PT-002 | Standard library only; self-implemented JSON Schema validator in `core.schema` |
| NFR-S-002 | Path restriction in `core.executor._run_script` |
| NFR-O-001 | JSONL output via `core.logger` |
| FR-070 | dispatcher is an independent process and does not reference other hooks |
| FR-071 | When `core.registry.load` returns an empty list, skip the executor and return ALLOW |
| FR-072 | README / docs description (execution-order specification) |
| FR-073 | Migration guide docs (§8.4) |
