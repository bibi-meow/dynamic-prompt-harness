# SWE.2 Software Architectural Design — dynamic-prompt-harness

**Scope**: Agreement on class structure, responsibility boundaries, dependency direction, and interface overview.
Internal implementation (algorithms, private methods, detailed error branching) is finalized in SWE.3 / during implementation.

**Decisions (agreed in brainstorming)**:
- Executor uses **subprocess style** (arbitrary command execution; bash/node/python can coexist)
- Registry entries use a **fixed schema + `frozen dataclass` + JSON Schema double defense**
- Exception handling uses a **core-defined `DPHError` hierarchy**, caught at the top of the dispatcher
- Adapters are **one pair per vendor** (`parse_input` / `format_output`)
- Registry is **loaded per invocation, filtered only by trigger type**

---

## 1. Module layout and class inventory

```mermaid
graph TB
    subgraph entry["entry point"]
        MAIN["__main__.py"]
        DSP["Dispatcher"]
    end
    subgraph adapters["adapters/"]
        CC["ClaudeCodeAdapter"]
    end
    subgraph core["core/"]
        IO["io_contract<br/>AbstractInput / AbstractResult / Entry / Decision"]
        REG["Registry"]
        EXE["Executor"]
        COM["Composer"]
        SCH["SchemaValidator"]
        LOG["JsonlLogger"]
        ERR["errors<br/>DPHError hierarchy"]
    end

    MAIN --> DSP
    DSP --> CC
    DSP --> REG
    DSP --> EXE
    DSP --> COM
    DSP --> LOG
    CC --> IO
    REG --> SCH
    REG --> IO
    EXE --> IO
    COM --> IO
    EXE --> ERR
    REG --> ERR
    CC --> ERR
```

| Module | Class / Type | Role |
|---|---|---|
| `core.io_contract` | `AbstractInput`, `AbstractResult`, `Entry`, `Decision` (Enum) | Frozen dataclass / Enum shared across all layers |
| `core.registry` | `Registry` | Loads `registry.json`, applies trigger filter, priority sort |
| `core.executor` | `Executor` | Runs `Entry` as subprocess; converts stdout/exit into `AbstractResult` |
| `core.composer` | `Composer` | Folds multiple `AbstractResult` via AND-composition |
| `core.schema` | `SchemaValidator` | Validates registry.json using stdlib only |
| `core.logger` | `JsonlLogger` | Appends JSONL; manages log_level granularity |
| `core.errors` | `DPHError`, `RegistryError`, `ExecutionError`, `SchemaError`, `AdapterError` | Exception hierarchy |
| `adapters.claude_code` | `ClaudeCodeAdapter` | Converts between Claude Code hook JSON and `Abstract*` |
| `dispatcher` | `Dispatcher` | Overall flow control; top-level exception handler |

---

## 2. Data structures (core.io_contract)

```mermaid
classDiagram
    class Decision {
        <<Enum>>
        ALLOW
        DENY
        HINT
    }

    class AbstractInput {
        <<frozen dataclass>>
        +trigger: str
        +tool: str | None
        +tool_input: dict
        +prompt: str | None
        +context: dict
    }

    class AbstractResult {
        <<frozen dataclass>>
        +decision: Decision
        +message: str | None
        +metadata: dict
    }

    class Entry {
        <<frozen dataclass>>
        +id: str
        +triggers: tuple[str, ...]
        +command: tuple[str, ...]
        +priority: int
        +timeout_sec: float
        +log_level: str | None
        +matcher: str | None
    }

    AbstractResult --> Decision
```

**Invariants**:
- `Entry.triggers` is a tuple of values drawn from `pre_tool_use` / `post_tool_use` / `user_prompt_submit` / `pre_compact` (no duplicates)
- `Entry.command` is a tuple (not a list) — guaranteed by frozen
- `AbstractInput.trigger` has the same value domain as Entry.triggers
- When `AbstractResult.decision == DENY`, `message` is required (so the composer can build a merged message)

---

## 3. Class relationship diagram (key interfaces)

```mermaid
classDiagram
    class Dispatcher {
        +run(trigger: str, raw_stdin: str) int
    }

    class ClaudeCodeAdapter {
        +parse_input(raw: str, trigger: str) AbstractInput
        +format_output(result: AbstractResult, trigger: str) tuple[str, int]
    }

    class Registry {
        +load(path: Path) Registry
        +entries_for(trigger: str, tool: str | None) list[Entry]
    }

    class Executor {
        +execute(entry: Entry, input: AbstractInput) AbstractResult
    }

    class Composer {
        +compose(results: list[AbstractResult]) AbstractResult
    }

    class SchemaValidator {
        +validate(data: dict) None
    }

    class JsonlLogger {
        +log(level: str, event: str, **fields) None
    }

    class DPHError {
        <<exception>>
    }
    class RegistryError
    class ExecutionError
    class SchemaError
    class AdapterError

    Dispatcher --> ClaudeCodeAdapter
    Dispatcher --> Registry
    Dispatcher --> Executor
    Dispatcher --> Composer
    Dispatcher --> JsonlLogger
    Registry --> SchemaValidator
    DPHError <|-- RegistryError
    DPHError <|-- ExecutionError
    DPHError <|-- SchemaError
    DPHError <|-- AdapterError
```

---

## 4. Execution sequence

```mermaid
sequenceDiagram
    participant CC as Claude Code
    participant M as __main__
    participant D as Dispatcher
    participant A as ClaudeCodeAdapter
    participant R as Registry
    participant E as Executor
    participant CO as Composer
    participant L as JsonlLogger

    CC->>M: python -m dph <trigger> (stdin: hook JSON)
    M->>D: run(trigger, stdin)
    D->>A: parse_input(stdin, trigger)
    A-->>D: AbstractInput
    D->>R: load(registry.json)
    R-->>D: Registry (validated)
    D->>R: entries_for(trigger, input.tool)
    R-->>D: [Entry...]  (priority sorted)
    loop each Entry
        D->>E: execute(entry, input)
        E-->>D: AbstractResult
        D->>L: log(execution)
        Note over D: break on DENY
    end
    D->>CO: compose(results)
    CO-->>D: merged AbstractResult
    D->>A: format_output(result, trigger)
    A-->>D: (stdout_json, exit_code)
    D-->>M: exit_code
    M-->>CC: stdout + exit
```

**Short-circuit condition**: as soon as any Entry returns `DENY`, subsequent Entries are not executed (FR-033).
**Empty registry**: when `entries_for` returns an empty list, Composer returns `AbstractResult(ALLOW, None, {})` (FR-071).

---

## 5. Dependency direction (Dependency Rules)

```mermaid
graph LR
    A[adapters.*] --> C[core.*]
    D[dispatcher] --> A
    D --> C
    C -.forbidden.-> A
    C -.forbidden.-> D
```

- **AP-2 restated**: core must not import adapters. This guarantees that adding a new vendor requires no changes to core.
- dispatcher is the top-level glue layer that may know about both.
- Within `core.*`, mutual dependencies flow only one way: `io_contract` / `errors` → everything else (`io_contract` is a leaf imported by other modules).

---

## 6. Exception hierarchy and responsibilities

```mermaid
classDiagram
    class DPHError {
        <<base>>
        +code: str
        +detail: dict
    }
    DPHError <|-- RegistryError
    DPHError <|-- ExecutionError
    DPHError <|-- SchemaError
    DPHError <|-- AdapterError
```

| Exception | Origin | Dispatcher handling |
|---|---|---|
| `SchemaError` | `SchemaValidator.validate` | log(error) → exit with ALLOW (do not break installation; FR-071 family) |
| `RegistryError` | `Registry.load` (IO / JSON parse) | Same as above |
| `ExecutionError` | `Executor.execute` (subprocess timeout / non-zero exit) | log(error) → skip this entry and continue |
| `AdapterError` | `parse_input` / `format_output` | log(error) → exit 0 / empty stdout (do not interfere with hook behavior) |
| Unknown exception | Anywhere | log(critical) → exit 0 fail-safe |

**Fail-safe principle**: bugs in the dispatcher itself must never stop Claude Code. DENY occurs only by explicit registry intent.

---

## 7. Interface summary (signatures only)

```python
# adapters/claude_code.py
class ClaudeCodeAdapter:
    def parse_input(self, raw: str, trigger: str) -> AbstractInput: ...
    def format_output(self, result: AbstractResult, trigger: str) -> tuple[str, int]: ...

# core/registry.py
class Registry:
    @classmethod
    def load(cls, path: Path) -> "Registry": ...
    def entries_for(self, trigger: str, tool: str | None) -> list[Entry]: ...

# core/executor.py
class Executor:
    def __init__(self, cwd: Path, logger: JsonlLogger) -> None: ...
    def execute(self, entry: Entry, input: AbstractInput) -> AbstractResult: ...

# core/composer.py
class Composer:
    def compose(self, results: list[AbstractResult]) -> AbstractResult: ...

# core/schema.py
class SchemaValidator:
    def validate(self, data: dict) -> None: ...  # raises SchemaError

# core/logger.py
class JsonlLogger:
    def __init__(self, path: Path, level: str) -> None: ...
    def log(self, level: str, event: str, **fields) -> None: ...

# dispatcher.py
class Dispatcher:
    def run(self, trigger: str, raw_stdin: str) -> int: ...
```

Internal private methods / algorithms / branching details are finalized in SWE.3 / during implementation (out of scope for this document).

---

## 8. Testability (SWE.2 perspective)

- **Unit isolation**: each class injects its dependencies via `__init__`; side effects (file IO, subprocess) are localized to `Executor` / `JsonlLogger` / `Registry.load`
- **Mock boundary**: swapping `Executor.execute` and `JsonlLogger.log` lets the dispatcher run end-to-end in memory
- **Contract test**: `ClaudeCodeAdapter` can be round-trip tested against real hook JSON samples (`.claude/settings.json` / official documentation)
- **Schema test**: `SchemaValidator` is covered by positive / negative fixtures

---

## 9. Traceability (SYS.3 → SWE.2)

| SYS.3 element | SWE.2 class |
|---|---|
| §4 adapters/claude_code | `ClaudeCodeAdapter` |
| §4 core.registry | `Registry` + `SchemaValidator` |
| §4 core.executor | `Executor` |
| §4 core.composer | `Composer` |
| §4 core.io_contract | `io_contract` dataclasses |
| §4 core.logger | `JsonlLogger` |
| §4 dispatcher | `Dispatcher` |
| §6 AP-2 (core→adapters forbidden) | §5 Dependency direction |
| §7 8-step processing sequence | §4 Execution sequence |
| §8 empty registry ALLOW | §4 note + §6 fail-safe |

---

## 10. Next steps

- [ ] Review this document
- [ ] SWE.3 Detailed Design (internal algorithms, private methods) — can proceed in parallel with implementation
- [ ] TDD: work red→green in the order `io_contract` → `SchemaValidator` → `Registry` → `Composer` → `Executor` → `ClaudeCodeAdapter` → `Dispatcher`
