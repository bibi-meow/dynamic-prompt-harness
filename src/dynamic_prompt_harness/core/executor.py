import json
import os
import subprocess
from pathlib import Path

from .io_contract import AbstractInput, AbstractResult, Decision, Entry
from .logger import JsonlLogger


class Executor:
    def __init__(self, cwd: Path, logger: JsonlLogger):
        self._cwd = cwd
        self._log = logger

    def execute(self, entry: Entry, input: AbstractInput) -> AbstractResult:
        stdin_payload = json.dumps(
            {
                "trigger": input.trigger,
                "tool": input.tool,
                "tool_input": input.tool_input,
                "tool_result": input.tool_result,
                "prompt": input.prompt,
                "context": input.context,
            }
        )
        env = {
            **os.environ,
            "DPH_ENTRY_ID": entry.id,
            "DPH_TRIGGER": input.trigger,
            "PYTHONIOENCODING": "utf-8",
        }
        if entry.log_level:
            env["DPH_LOG_LEVEL"] = entry.log_level
        try:
            proc = subprocess.run(
                list(entry.command),
                input=stdin_payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=entry.timeout_sec,
                cwd=str(self._cwd),
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            self._log.log("error", "executor_timeout", entry_id=entry.id)
            return AbstractResult(Decision.DENY, f"[{entry.id}] timeout", {"reason": "timeout"})
        except OSError as e:
            self._log.log("error", "executor_oserror", entry_id=entry.id, err=str(e))
            return AbstractResult(
                Decision.DENY,
                f"[{entry.id}] oserror: {e}",
                {"reason": "oserror"},
            )

        if proc.returncode != 0:
            self._log.log(
                "error",
                "executor_nonzero",
                entry_id=entry.id,
                rc=proc.returncode,
                stderr=proc.stderr[:500],
            )
            return AbstractResult(
                Decision.DENY,
                f"[{entry.id}] exit {proc.returncode}: {proc.stderr.strip()}",
                {"reason": "nonzero_exit", "rc": proc.returncode},
            )

        out = proc.stdout.strip()
        if not out:
            return AbstractResult(Decision.ALLOW, None, {})
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            self._log.log("error", "executor_bad_stdout", entry_id=entry.id, stdout=out[:200])
            return AbstractResult(
                Decision.DENY,
                f"[{entry.id}] invalid decision JSON",
                {"reason": "unparseable_stdout"},
            )

        decision_raw = parsed.get("decision", "allow")
        try:
            decision = Decision(decision_raw)
        except ValueError:
            decision = Decision.ALLOW
        return AbstractResult(decision, parsed.get("message"), parsed.get("metadata") or {})
