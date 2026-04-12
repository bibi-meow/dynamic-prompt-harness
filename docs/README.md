# Documentation Index

dph documentation follows the [Diátaxis](https://diataxis.fr/) framework:
four quadrants, each serving a different reader need.

| Quadrant | Goal | Docs |
|---|---|---|
| **Tutorial** | Learning-oriented — hand-held first run | [01-first-harness.md](tutorial/01-first-harness.md) |
| **How-to** | Task-oriented — recipes for real problems | [add-custom-harness.md](how-to/add-custom-harness.md), [coexist-with-other-hooks.md](how-to/coexist-with-other-hooks.md), [troubleshoot.md](how-to/troubleshoot.md) |
| **Reference** | Information-oriented — precise specs | [registry-schema.md](reference/registry-schema.md), [triggers.md](reference/triggers.md), [subprocess-contract.md](reference/subprocess-contract.md), [cli.md](reference/cli.md), [harness-patterns.md](reference/harness-patterns.md) |
| **Explanation** | Understanding-oriented — design rationale | [dynamic-prompting.md](explanation/dynamic-prompting.md), [philosophy.md](explanation/philosophy.md), [architecture.md](explanation/architecture.md) |

Start with [explanation/dynamic-prompting.md](explanation/dynamic-prompting.md)
for the three theses that motivate dph — necessity, sufficiency,
and boundary — then
[reference/harness-patterns.md](reference/harness-patterns.md) for the
six reusable patterns those theses produce in practice.

## Engineering record (ASPICE-aligned)

The `sys/` and `swe/` directories preserve the requirements
elicitation and architectural design that produced this codebase.
They are historical artifacts — read them when you want to see the
engineering rigor behind decisions documented in `explanation/`.

- [sys/sys.1-requirements-elicitation.md](sys/sys.1-requirements-elicitation.md)
- [sys/sys.2-system-requirements.md](sys/sys.2-system-requirements.md)
- [sys/sys.3-architectural-design.md](sys/sys.3-architectural-design.md)
- [swe/swe.2-software-architecture.md](swe/swe.2-software-architecture.md)
