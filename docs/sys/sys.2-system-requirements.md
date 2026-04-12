# SYS.2 System Requirements Analysis: dynamic-prompt-harness

Functional requirements / non-functional requirements / interface requirements /
constraints derived from SYS.1 (user-stories). v0.1 scope.

## 1. Functional Requirements (FR)

### 1.1 Distribution / Initialization

| ID | Requirement | Source US |
|---|---|---|
| FR-001 | Installation via `/plugin install` through the Claude Code plugin marketplace is supported | A1 |
| FR-002 | A slash command (`/dph-init`) generates `registry.json` (empty/template) and the `harnesses/` directory under `.claude/dynamic-prompt-harness/` in the current project | A2 |
| FR-003 | The plugin's `hooks.json` automatically registers the dispatcher hook for PreToolUse / PostToolUse / UserPromptSubmit / PreCompact | A3 |

### 1.2 Dispatcher

| ID | Requirement | Source US |
|---|---|---|
| FR-010 | The dispatcher receives the above 4 triggers through a single entry point | C1 |
| FR-011 | On startup, the dispatcher loads `.claude/dynamic-prompt-harness/registry.json` | B1 |
| FR-012 | The dispatcher performs coarse filtering of each registry entry by `trigger + tool + pattern`, and only runs matched harnesses as subprocesses | C2 |
| FR-013 | The dispatcher executes matched harnesses in ascending `priority` order. Ties are resolved by registry declaration order | C3, B3 |
| FR-014 | Upon detecting `decision = deny` from a harness, the dispatcher skips subsequent harnesses and returns the final result as `deny` (short-circuit) | C3 |
| FR-015 | The dispatcher concatenates all `decision = hint` messages into a single output | C4 |
| FR-016 | The dispatcher catches abnormal termination (non-zero exit) / malformed JSON output from individual harnesses, skips the offending harness, and continues with the rest. Forced termination on hang is not performed; this is delegated to the Claude Code hook timeout | C5 |
| FR-017 | The dispatcher records caught anomalies in the log (timestamp / session_id / trigger / harness name / cause / exit code) | C5 |
| FR-018 | The dispatcher log level (`debug` / `info` / `warn` / `error`) can be switched via the environment variable `DPH_LOG_LEVEL` or the top-level `log_level` field in `registry.json`. Default is `info` | NFR-O |

### 1.3 Registry

| ID | Requirement | Source US |
|---|---|---|
| FR-020 | `registry.json` is validated against a JSON Schema. On validation failure, an error message is written to stderr and dispatcher startup is aborted | B4 |
| FR-021 | A registry entry has the following fields: `name` (required, unique), `triggers` (required, array), `tools` (optional, array), `pattern` (optional, regex string), `priority` (optional, integer, default 100), `enabled` (optional, bool, default true). In addition, it must have exactly one of `script` or `action` (mutually exclusive, required) | B1, B2, B3 |
| FR-021a | The `action` field represents a declarative harness. Form: `{"on_match": "deny" / "allow" / "hint", "message": "<string>"}`. The dispatcher does not spawn a subprocess; on pattern match it returns this result directly | B5 (declarative extension) |
| FR-021b | The `script` field represents a custom-implementation harness. Form: a relative path under `.claude/dynamic-prompt-harness/harnesses/`. The dispatcher executes the specified script as a subprocess | B5 |
| FR-022 | Entries with `enabled: false` are ignored by the dispatcher | B2 |

### 1.4 Abstract I/O Contract

| ID | Requirement | Source US |
|---|---|---|
| FR-030 | Harnesses receive the abstract input JSON on stdin | B5, D2 |
| FR-031 | The abstract input has the fields `trigger`, `tool`, `tool_input`, `context`. `context` carries vendor-provided parameters obtainable only through the hook (`session_id`, `cwd`, `transcript_path`, `hook_event_name`, etc.), passed through by the dispatcher as-is. Harnesses can reference `context.session_id` and the like | D2 |
| FR-031a | Of all Claude Code hook JSON fields, the dispatcher passes through those mappable to the abstract I/O into `context`. Vendor-specific names (e.g. `hookSpecificOutput`) are stored under names normalized by the adapter, not under their original names | D2, D3 |
| FR-032 | Harnesses return the abstract output JSON on stdout. Fields: `decision` (required, `allow` / `deny` / `hint`), `message` (optional), `metadata` (optional, dict) | B5 |
| FR-033 | Harnesses may be implemented in any language (subject to compliance with the stdin/stdout contract) | B5 |

### 1.5 Adapter

| ID | Requirement | Source US |
|---|---|---|
| FR-040 | Conversion between the Claude Code-specific hook JSON (I/O) and the abstract I/O is confined to the adapter layer | C6, D1 |
| FR-041 | Vendor-specific extension fields (such as Claude Code's `hookSpecificOutput`) can be expressed via `metadata` in the abstract output. The adapter maps them to the vendor-specific fields | D3 |
| FR-042 | Adding a future vendor is designed to be completed solely by adding `adapters/<vendor>.py` (without modifying existing core / harnesses) | D1 |

### 1.6 Concrete Harness Behavior (Pattern Expressibility)

The 6 patterns in v0.1 scope must be expressible using only the abstract I/O.

| ID | Pattern | Requirement | Source US |
|---|---|---|---|
| FR-050 | Gate | **Expressible declaratively.** `action = {on_match: deny, message: ...}` | E1 |
| FR-051 | Guide | **Expressible declaratively.** `action = {on_match: hint, message: ...}` | E2 |
| FR-052 | Validator | PostToolUse trigger. Simple cases are declarative; when inspecting output content dynamically, use `script` | E3 |
| FR-053 | Guard | PreToolUse. Declarative when preconditions do not depend on external state; `script` otherwise | E4 |
| FR-054 | Circuit Breaker | Requires counter persistence, so `script` is mandatory. Implemented inside the harness | E5 |
| FR-055 | Monitor | PostToolUse, side-effect only. Log emission and the like require harness-internal implementation; `script` as a rule | E6 |

### 1.7a Coexistence with Existing Hooks

| ID | Requirement | Source US |
|---|---|---|
| FR-070 | The dispatcher neither references nor modifies other Claude Code hooks (those the user has already registered in `settings.json`). It operates as an independent process | F1 |
| FR-071 | When `entries` in `registry.json` is empty or there are zero matching entries for the trigger, the dispatcher returns ALLOW and exits normally (exit code 0) | F4 |
| FR-072 | Execution-order control via `priority` is scoped to dph-internal harnesses. Ordering relative to other hooks follows the Claude Code hook specification. This is stated explicitly in the README / docs | F3 |
| FR-073 | A migration guide for gradually moving existing hooks into the dph registry is provided as documentation (including steps to remove migrated logic from `settings.json` to avoid double execution) | F2 |

### 1.7 State Management Policy

State management features (DS/DE/RS/RC, etc.) are out of scope for the framework.
When state-dependent patterns such as Stateful Gate / Shield / Workflow are required,
users must implement their own persistence layer (file / SQLite / etc.) inside
`script`-type harnesses. The framework provides no state-related API or extension point.

This policy is invariant across v0.1 / v0.2+.

## 2. Non-Functional Requirements (NFR)

### 2.1 Performance

| ID | Requirement |
|---|---|
| NFR-P-001 | Dispatcher processing time (from hook reception to result return) shall target within 100ms when there are no matching harnesses (excluding subprocess startup cost) |
| NFR-P-002 | Declarative harnesses (`action`) must be orders of magnitude faster than script-type since they are processed without subprocess startup |

### 2.2 Reliability

| ID | Requirement |
|---|---|
| NFR-R-001 | Even if one harness terminates abnormally / times out, processing of other harnesses for the same event continues |
| NFR-R-002 | On registry load failure, the dispatcher is not started and the Claude Code hook is passed through with the default (allow) (fail-open). The fact of fail-open is recorded to stderr |

### 2.3 Portability

| ID | Requirement |
|---|---|
| NFR-PT-001 | Runs on Windows / Linux / macOS |
| NFR-PT-002 | Execution uses only the Python 3.9+ standard library (zero external dependencies) |
| NFR-PT-003 | Harness code is vendor-independent. The same script works under a future, different vendor adapter (subject to compliance with the abstract I/O contract) |

### 2.4 Extensibility

| ID | Requirement |
|---|---|
| NFR-E-001 | Adding a new harness is completed by editing `registry.json` and placing scripts only (no dispatcher / core code change required) |
| NFR-E-002 | Adding a new vendor adapter is completed by creating a new `adapters/<vendor>.py` file only |
| NFR-E-003 | Declarative harnesses (`action`) enable script-free simple harnesses to be added via registry edits alone |

### 2.5 Maintainability

| ID | Requirement |
|---|---|
| NFR-M-001 | The 3-layer structure (adapter / core / harness) is physically separated at the directory level |
| NFR-M-002 | Core code does not import vendor-specific symbols |

### 2.6 Security

| ID | Requirement |
|---|---|
| NFR-S-001 | The dispatcher only launches scripts declared in `registry.json` (no arbitrary-path execution) |
| NFR-S-002 | Harness script paths are restricted to under `.claude/dynamic-prompt-harness/harnesses/` (`../` traversal forbidden) |

### 2.7 Observability

| ID | Requirement |
|---|---|
| NFR-O-001 | Dispatcher execution logs (timestamp / session_id / trigger / harness name / result / error) are appended to `.claude/dynamic-prompt-harness/logs/` in JSONL format |
| NFR-O-002 | Log level supports the 4 levels `debug` / `info` / `warn` / `error` (FR-018) |
| NFR-O-003 | Log rotation / retention period is out of scope in v0.1 (user's responsibility) |

## 3. Interface Requirements (IR)

| ID | Interface | Spec Reference |
|---|---|---|
| IR-001 | Claude Code hook input JSON | Claude Code official hook spec |
| IR-002 | Claude Code hook output JSON | Claude Code official hook spec |
| IR-003 | Abstract input JSON (dispatcher → harness) | FR-031 |
| IR-004 | Abstract output JSON (harness → dispatcher) | FR-032 |
| IR-005 | `registry.json` schema | FR-021 |
| IR-006 | Plugin manifest `.claude-plugin/plugin.json` | Claude Code plugin spec |
| IR-007 | Plugin hooks registration `hooks/hooks.json` | Claude Code plugin spec |

## 4. Constraints (CON)

| ID | Constraint |
|---|---|
| CON-001 | v0.1 does not include state management features (treated as a separate package in v0.2+) |
| CON-002 | v0.1 provides only the Claude Code adapter |
| CON-003 | Dispatcher / adapter / core are implemented in Python |
| CON-004 | External Python dependencies (`requirements.txt`, etc.) shall not be introduced |
| CON-005 | Distribution follows the Claude Code plugin marketplace format |

## 5. Traceability

The US-to-requirement mapping is shown below (the reverse trace is in the "Source US" column of each FR table).

| US | Corresponding FR |
|---|---|
| US-A1 | FR-001 |
| US-A2 | FR-002 |
| US-A3 | FR-003 |
| US-B1 | FR-011, FR-021, NFR-E-001 |
| US-B2 | FR-021, FR-022 |
| US-B3 | FR-013, FR-021 |
| US-B4 | FR-020 |
| US-B5 | FR-030, FR-032, FR-033, FR-021b |
| US-B6 | FR-021, FR-021a, NFR-E-003 |
| US-C1 | FR-010 |
| US-C2 | FR-012 |
| US-C3 | FR-013, FR-014 |
| US-C4 | FR-015 |
| US-C5 | FR-016, FR-017, NFR-R-001 |
| US-C6 | FR-040 |
| US-D1 | FR-040, FR-042, NFR-M-002 |
| US-D2 | FR-030, FR-031, NFR-PT-003 |
| US-D3 | FR-041 |
| US-E1 | FR-050 |
| US-E2 | FR-051 |
| US-E3 | FR-052 |
| US-E4 | FR-053 |
| US-E5 | FR-054 |
| US-E6 | FR-055 |
| US-E7 | (out of framework scope — section 1.7, implement inside harness) |
| US-E8 | (out of framework scope — section 1.7, implement inside harness) |
| US-E9 | (out of framework scope — section 1.7, implement inside harness) |
| US-F1 | FR-070 |
| US-F2 | FR-073 |
| US-F3 | FR-072 |
| US-F4 | FR-071 |
