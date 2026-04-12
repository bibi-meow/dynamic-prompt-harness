# Explanation: Philosophy

dph starts from two theses about prompting. Everything that follows
— the registry, the composer, the subprocess contract, the fail-safe
defaults — is a consequence of those two starting points.

## Starting point: the two theses

**Thesis 1 — Necessity.** Static prompts have structural limits
(Lost in the Middle, hallucination, drift on long runs). Reliable
behavior requires prompts injected into the running context, on the
events that make them relevant.

**Thesis 2 — Sufficiency.** Event-driven injection is expressive
enough to realize any workflow you can draw as a UML activity
diagram; each primitive (action, decision, merge, fork, loop, guard,
end) has a direct hook counterpart.

Both theses, and the activity-to-hook mapping, are spelled out in
[dynamic-prompting.md](dynamic-prompting.md). dph exists because the
theses together imply we should stop writing longer static rules and
start running small scripts at event boundaries.

## Design principles

The theses justify the idea. The principles below justify dph's
specific shape.

### Registry over scripts

A single growing hook script is a liability: rules entangle, tests
get hard, and removing one rule risks regressing another. A
**registry of small entries** inverts this. Each rule is isolated in
its own subprocess and file, composable by editing JSON, testable
with stdin/stdout fixtures, and observable as its own log record.

### AND-composition with DENY-wins

When many rules see the same event, they must compose safely. dph's
composer uses AND: **any DENY wins**. Every rule is a veto; the
strictest rule sets the bar. HINTs, being advisory, concatenate. A
rule that could override another's DENY would be unsafe by
construction, so the composer does not expose that capability.

### Subprocess execution

Harnesses run as subprocesses. That makes them **language-neutral**:
Python for quick checks, bash for grep-style filters, Node for JS
teams, Go for performance-sensitive rules. The contract is just
stdin JSON in, stdout JSON out. Per-invocation process overhead is
measured in milliseconds — negligible for safety rules.

### Vendor-neutral core with adapters

Claude Code is today's target, not the only target. The **core** —
registry, executor, composer — knows nothing about Claude. **Adapters**
translate vendor-specific hook payloads into the abstract input
harnesses see. One adapter exists now; adding another reuses
everything else unchanged.

### Fail-safe always

A broken registry or harness must not brick the agent. dph uses
asymmetric defaults across two failure domains:

| Failure | Default | Why |
|---|---|---|
| Per-entry (a harness crashes / times out / emits invalid JSON) | DENY | A broken safety rule must not silently disappear |
| Dispatcher (dph itself crashes, missing registry, unknown exception) | ALLOW + critical log | A broken harness-of-harnesses must not block every tool call |

The user can always disable dph by removing the hook wiring or
deleting `registry.json`; they cannot easily recover from an agent
that refuses every tool because dph itself crashed.

### Invisible to the agent

The agent experiences dph as **advice and redirects**, not as
bureaucracy. HINTs arrive as additional context the model can read.
DENIALs arrive with a short reason that points at the fix. There is
no "approval queue" the agent must navigate, no status codes to
memorize. A well-tuned registry feels, from inside the agent, like a
slightly more capable environment.

## Non-goals

Stating what dph does **not** try to be is as important as stating
what it is.



- **Harness engineering (stage 3).** dph does not provide
  Brain/Hands/Session separation, session persistence, or
  orchestration loops. Those belong to the harness dph plugs into.
  See [dynamic-prompting.md](dynamic-prompting.md) Thesis 3.
- **State management.** dph core is stateless. Harnesses that need
  state (counters, caches, rolling windows) own their own storage.
  The Circuit Breaker pattern is the canonical example — see
  [../reference/harness-patterns.md](../reference/harness-patterns.md).
- **Workflow orchestration.** dph reacts to events; it does not
  schedule work, chain jobs, or manage long-running flows. Use an
  external orchestrator when you need that.
- **Cross-session coordination.** One dph instance serves one agent
  session. Coordinating multiple concurrent agents is out of scope.

These boundaries keep the core small, the contract stable, and the
failure modes easy to reason about.

## See also

- Anthropic, *Managed Agents* — harness defined as "the loop that
  calls Claude":
  https://www.anthropic.com/engineering/managed-agents
- *12 Agentic Harness Patterns* (generativeprogrammer.com) — a
  broader pattern taxonomy that spans stages 2 and 3:
  https://generativeprogrammer.com/p/12-agentic-harness-patterns-from
