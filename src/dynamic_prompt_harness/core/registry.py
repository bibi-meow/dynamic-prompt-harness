from __future__ import annotations
import json, re
from pathlib import Path
from .io_contract import Entry
from .schema import SchemaValidator
from .errors import RegistryError, SchemaError

class Registry:
    def __init__(self, entries: tuple[Entry, ...], compiled_matchers: dict[str, re.Pattern]):
        self._entries = entries
        self._compiled = compiled_matchers

    @classmethod
    def load(cls, path: Path) -> "Registry":
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as e:
            raise RegistryError(f"cannot read {path}: {e}") from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RegistryError(f"invalid JSON: {e}") from e
        try:
            SchemaValidator().validate(data)
        except SchemaError as e:
            raise RegistryError(str(e), code=e.code, detail=e.detail) from e

        entries = tuple(cls._to_entry(d) for d in data["entries"])
        compiled: dict[str, re.Pattern] = {}
        for d, ent in zip(data["entries"], entries):
            if ent.matcher is not None:
                # Schema has already validated compilability; safe to compile here.
                compiled[ent.id] = re.compile(ent.matcher)
        return cls(entries, compiled)

    @staticmethod
    def _to_entry(d: dict) -> Entry:
        return Entry(
            id=d["id"],
            triggers=tuple(d["triggers"]),
            command=tuple(d["command"]),
            priority=int(d.get("priority", 0)),
            timeout_sec=float(d.get("timeout_sec", 30.0)),
            log_level=d.get("log_level"),
            matcher=d.get("matcher"),
        )

    def entries_for(self, trigger: str, tool: str | None) -> list[Entry]:
        picked = [e for e in self._entries if trigger in e.triggers and self._matches(e, tool)]
        return sorted(picked, key=lambda e: -e.priority)

    def _matches(self, entry: Entry, tool: str | None) -> bool:
        if entry.matcher is None:
            return True
        if tool is None:
            return False
        pat = self._compiled.get(entry.id)
        if pat is None:
            return False
        return pat.fullmatch(tool) is not None
