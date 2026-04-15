from .io_contract import AbstractResult, Decision, Entry

class Composer:
    def compose(self, results: list[AbstractResult], entries: list[Entry] | None = None) -> AbstractResult:
        if not results:
            return AbstractResult(Decision.ALLOW, None, {})

        per_entry: dict[str, dict] = {}
        if entries is not None and len(entries) == len(results):
            for ent, res in zip(entries, results):
                per_entry[ent.id] = dict(res.metadata or {})
        meta = {"per_entry": per_entry} if per_entry else {}

        denies = [r for r in results if r.decision is Decision.DENY]
        if denies:
            msg = "; ".join(r.message for r in denies if r.message) or "denied"
            return AbstractResult(Decision.DENY, msg, meta)
        hints = [r for r in results if r.decision is Decision.HINT]
        if hints:
            msg = "; ".join(r.message for r in hints if r.message) or None
            return AbstractResult(Decision.HINT, msg, meta)
        return AbstractResult(Decision.ALLOW, None, meta)
