# User Stories: dynamic-prompt-harness

A general-purpose runtime for dynamic prompt injection / harness engineering
via Claude Code hooks. The core value is a mechanism to add concrete harnesses
ad-hoc; providing templates is a secondary concern.

## Prerequisites (Decisions)

| Item | Decision |
|---|---|
| Repo / plugin name | `dynamic-prompt-harness` |
| Unit of addition | Declarative harness (registry only) or 1 harness = 1 script |
| Dispatcher | A single hook receives all triggers |
| Registry | Centralized `registry.json` |
| I/O contract | Abstraction layer present (vendor-agnostic) |
| Composition | Priority + short-circuit; same priority follows registration order |
| State | Out of framework scope (implement per-harness if needed) |
| Language | Python (dispatcher/adapter) |
| Matcher | Two stages (coarse in registry + fine in harness) |
| Location (plugin) | `.claude/plugins/dynamic-prompt-harness/` |
| Location (user data) | `.claude/dynamic-prompt-harness/` |
| Distribution | Claude plugin + marketplace |
| v0.1 scope | dispatcher + registry + adapter only |

## Stakeholders

- **Project operator**: deploys the runtime and manages the registry
- **Harness author**: adds concrete harnesses
- **LLM agent**: the control target (constrained by hooks)
- **Framework developer**: maintains dynamic-prompt-harness itself

## A. Installation and Initialization

### US-A1
As a project operator, I can install the runtime via
`/plugin install dynamic-prompt-harness@<marketplace>` without placing files
manually.

### US-A2
As a project operator, I can generate the
`.claude/dynamic-prompt-harness/` skeleton (registry.json + harnesses/)
in my project via a slash command (e.g., `/dph-init`).

### US-A3
As a project operator, the dispatcher hook is automatically registered into
the equivalent of settings.json at install time (relying on the plugin's
hooks.json mechanism).

## B. Adding and Updating Harnesses

### US-B1
As an author, a harness becomes active simply by placing a script under
`.claude/dynamic-prompt-harness/harnesses/` and adding an entry to
`registry.json` (no dispatcher code changes required).

### US-B2
As an author, I can disable an individual harness via the `enabled` flag in
the registry (leaving the script in place).

### US-B3
As an author, I can control execution order via the `priority` integer.
Entries with the same priority execute in registration order within
`registry.json`.

### US-B4
As an author, `registry.json` is schema-validated, and invalid entries
produce a clear error message (never silently ignored).

### US-B5
As an author, I can write a harness in any language (bash / python / node,
etc.) as long as the stdin/stdout contract is followed.

### US-B6
As an author, for simple cases where a pattern hit maps directly to
`deny` / `allow` / `hint` with a fixed message, I can add a harness purely
by declaration in registry.json without writing a script
(declarative harness).

## C. Runtime Behavior

### US-C1
The framework receives PreToolUse / PostToolUse / UserPromptSubmit /
PreCompact through a single dispatcher.

### US-C2
The dispatcher performs coarse filtering by `trigger + tool + pattern`
before spawning subprocesses.

### US-C3
Matching harnesses are executed in priority order; same-priority entries
follow registration order in `registry.json`. Execution short-circuits on
the first DENY.

### US-C4
HINT outputs are concatenated from all harnesses into a single output.

### US-C5
Timeouts or crashes in individual harnesses are caught by the dispatcher,
logged, the offending harness is skipped, and subsequent execution continues.

### US-C6
Translation between abstract I/O and vendor-specific hook JSON is the sole
responsibility of the adapter layer. Vendor-specific code does not appear in
core or in harnesses.

## D. Vendor Abstraction

### US-D1
As a developer, Claude Code-specific logic is confined to
`adapters/claude_code.py`, so adding an adapter for Cursor / Gemini / etc.
requires only a new file.

### US-D2
As an author, harness code is vendor-independent. The same script runs on
another vendor provided an adapter exists.

### US-D3
Vendor-specific features (e.g., Claude Code's `hookSpecificOutput`) are
expressible via adapter metadata. Vendor-specific fields do not leak into
harness code.

## E. Concrete Harness Behaviors (Guaranteeing Pattern Expressibility)

Six stateless patterns are elaborated as user stories in v0.1.
Three state-dependent patterns are deferred to [v0.2+]; only the extension
points are guaranteed.

### US-E1 — Gate
When the LLM attempts an operation matching a deny pattern, it is blocked
together with a recommended alternative message
(e.g., `git add` of a `.env` file).

### US-E2 — Guide
When the LLM completes a step, it receives a HINT for the next step
(e.g., after commit completion, push is recommended).

### US-E3 — Validator
When the LLM's output fails a check, it receives a corrective HINT
(e.g., when a new function is added but the test file is missing,
a proposal to add a test).

### US-E4 — Guard
When preconditions are unmet, the operation is blocked together with the
procedure to satisfy them (e.g., when `/compact` runs without a diary
entry, the diary-write procedure is presented).

### US-E5 — Circuit Breaker
When the same error occurs N or more times, subsequent operations of the
same kind are blocked and a HINT escalating to a human is provided.

### US-E6 — Monitor
Observation-only at PostToolUse (always ALLOW, log output). Metrics can
be collected without mutating state.

### US-E7 — Stateful Gate (out of framework scope)
If DS/DE stateful decisions are required, the harness author implements a
dedicated persistence layer (file / SQLite / etc.) inside a `script`-type
harness. The framework provides no state-management API.

### US-E8 — Shield (out of framework scope)
Protecting in-use resources is likewise implemented inside the harness.

### US-E9 — Workflow (out of framework scope)
Multi-step state transitions are likewise implemented inside the harness.

## F. Coexistence with Existing Hooks

### US-F1
As a project operator, I can install dynamic-prompt-harness while keeping
custom hooks already registered in `settings.json`, without breaking them.
dph runs as an independent hook process and does not reference or modify
other hooks.

### US-F2
As a project operator, I can migrate existing hook logic into the registry
incrementally; migrated items are removed from `settings.json` to avoid
double execution (a migration guide is provided).

### US-F3
As a project operator, I explicitly understand that dph's `priority`
controls only the order among dph's internal harnesses, while the ordering
between dph and other hooks follows Claude Code's hook specification.

### US-F4
As a project operator, the dispatcher returns ALLOW and exits normally
even when `registry.json` has zero entries (the empty state immediately
after install does not break existing functionality).

## Coverage Check

### Stakeholder Coverage
| Stakeholder | Applicable US |
|---|---|
| Project operator | A1, A2, A3, F1, F2, F3, F4 |
| Harness author | B1, B2, B3, B4, B5, B6, D2 |
| LLM agent | E1-E9 |
| Framework developer | C1-C6, D1, D3 |

### Counts per Category
- (A) Installation and Initialization: 3
- (B) Adding and Updating Harnesses: 6
- (C) Runtime Behavior: 6
- (D) Vendor Abstraction: 3
- (E) Concrete Harness Behaviors: 9 (6 in framework scope, 3 out of scope)
- (F) Coexistence with Existing Hooks: 4

**Total user stories in framework scope: 28** (the 3 out-of-scope items
are documented as user responsibility)
