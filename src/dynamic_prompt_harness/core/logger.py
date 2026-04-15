import json, time
from pathlib import Path

# Canonical spelling is "warning"; "warn" kept as backward-compat alias.
_ORDER = {"debug": 10, "info": 20, "warning": 30, "warn": 30, "error": 40, "critical": 50}

class JsonlLogger:
    def __init__(self, path: Path, level: str = "info"):
        self._path = path
        self._threshold = _ORDER.get(level, 20)
        path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, event: str, **fields) -> None:
        if _ORDER.get(level, 0) < self._threshold:
            return
        rec = {"ts": time.time(), "level": level, "event": event, **fields}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
