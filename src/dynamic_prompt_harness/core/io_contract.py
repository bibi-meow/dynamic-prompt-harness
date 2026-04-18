from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    HINT = "hint"


@dataclass(frozen=True)
class AbstractInput:
    trigger: str
    tool: str | None
    tool_input: dict
    tool_result: dict | None
    prompt: str | None
    context: dict


@dataclass(frozen=True)
class AbstractResult:
    decision: Decision
    message: str | None
    metadata: dict


@dataclass(frozen=True)
class Entry:
    id: str
    triggers: tuple[str, ...]
    command: tuple[str, ...]
    priority: int
    timeout_sec: float
    log_level: str | None
    matcher: str | None
