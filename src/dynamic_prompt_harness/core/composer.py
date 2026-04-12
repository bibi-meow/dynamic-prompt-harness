from .io_contract import AbstractResult, Decision

class Composer:
    def compose(self, results: list[AbstractResult]) -> AbstractResult:
        if not results:
            return AbstractResult(Decision.ALLOW, None, {})
        denies = [r for r in results if r.decision is Decision.DENY]
        if denies:
            msg = "\n".join(r.message or "" for r in denies if r.message)
            return AbstractResult(Decision.DENY, msg or "denied", {})
        hints = [r for r in results if r.decision is Decision.HINT]
        if hints:
            msg = "\n".join(r.message or "" for r in hints if r.message)
            return AbstractResult(Decision.HINT, msg, {})
        return AbstractResult(Decision.ALLOW, None, {})
