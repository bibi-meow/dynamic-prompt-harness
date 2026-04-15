from __future__ import annotations
import os, sys
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
        try:
            inp = self._adapter.parse_input(raw_stdin, trigger)
            if not self._registry_path.exists():
                return self._adapter.format_output(
                    AbstractResult(Decision.ALLOW, None, {}), trigger)
            registry = Registry.load(self._registry_path)
            entries = registry.entries_for(trigger, inp.tool)
            executor = Executor(cwd=self._base, logger=self._logger)
            results: list[AbstractResult] = []
            for e in entries:
                r = executor.execute(e, inp)
                results.append(r)
            merged = Composer().compose(results, entries)
            return self._adapter.format_output(merged, trigger)
        except DPHError as e:
            self._logger.log("error", "dispatcher_dph_error", err=str(e), code=e.code)
            return "", 0  # fail-safe
        except Exception as e:
            self._logger.log("critical", "dispatcher_unknown", err=str(e))
            return "", 0

    def run(self, trigger: str, raw_stdin: str) -> int:
        out, rc = self.run_capture(trigger, raw_stdin)
        if out:
            sys.stdout.write(out)
        return rc
