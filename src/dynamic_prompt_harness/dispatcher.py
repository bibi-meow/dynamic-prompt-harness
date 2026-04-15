from __future__ import annotations
import os, sys, time
from pathlib import Path
from .adapters.claude_code import ClaudeCodeAdapter
from .core.registry import Registry
from .core.executor import Executor
from .core.composer import Composer
from .core.logger import JsonlLogger
from .core.io_contract import AbstractResult, Decision
from .core.errors import DPHError

class Dispatcher:
    def __init__(self, base: Path):
        self._base = Path(base)
        self._dph_dir = self._base / ".claude" / "dynamic-prompt-harness"
        reg_env = os.environ.get("DPH_REGISTRY_PATH")
        log_env = os.environ.get("DPH_LOG_PATH")
        self._registry_path = Path(reg_env) if reg_env else self._dph_dir / "registry.json"
        self._log_path = Path(log_env) if log_env else self._dph_dir / "logs" / "dph.log"
        level = os.environ.get("DPH_LOG_LEVEL", "info")
        self._logger = JsonlLogger(self._log_path, level=level)
        self._adapter = ClaudeCodeAdapter()

    def run_capture(self, trigger: str, raw_stdin: str) -> tuple[str, int]:
        t0 = time.monotonic()
        try:
            inp = self._adapter.parse_input(raw_stdin, trigger)
            if not self._registry_path.exists():
                return self._adapter.format_output(
                    AbstractResult(Decision.ALLOW, None, {}), trigger)
            registry = Registry.load(self._registry_path)
            entries = registry.entries_for(trigger, inp.tool)
            executor = Executor(cwd=self._base, logger=self._logger)
            results: list[AbstractResult] = []
            per_entry_outcomes: list[dict] = []
            for e in entries:
                te0 = time.monotonic()
                r = executor.execute(e, inp)
                dur_ms = (time.monotonic() - te0) * 1000.0
                results.append(r)
                per_entry_outcomes.append({
                    "id": e.id,
                    "decision": r.decision.value,
                    "message": r.message,
                    "metadata": dict(r.metadata or {}),
                    "duration_ms": dur_ms,
                })
            merged = Composer().compose(results, entries)
            latency_ms = (time.monotonic() - t0) * 1000.0
            self._logger.log(
                "info", "dph_decision",
                trigger=trigger,
                matched_entries=[e.id for e in entries],
                per_entry_outcomes=per_entry_outcomes,
                final_decision=merged.decision.value,
                final_message=merged.message,
                latency_ms=latency_ms,
            )
            return self._adapter.format_output(merged, trigger)
        except DPHError as e:
            self._logger.log("error", "dispatcher_dph_error", err=str(e), code=e.code)
            return "", 0
        except Exception as e:
            self._logger.log("critical", "dispatcher_unknown", err=str(e))
            return "", 0

    def run(self, trigger: str, raw_stdin: str) -> int:
        out, rc = self.run_capture(trigger, raw_stdin)
        if out:
            sys.stdout.write(out)
        return rc
