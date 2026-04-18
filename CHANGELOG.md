# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-04-18

### Added
- GitHub Actions CI: lint (ruff), test (pytest matrix: ubuntu/windows × 3.11-3.13), zero-dependency guard (pyproject.toml + AST scan). (PR #1 by cicd)
- Ruff configuration: E/F/W/I/N/UP/B/SIM rules, line-length 100, target-version py311.

### Fixed
- **Windows cp932 mojibake**: Executor now uses `encoding="utf-8"` and `PYTHONIOENCODING=utf-8` for subprocess communication. Adapter `format_output` uses `ensure_ascii=True` to keep `\uXXXX` escapes through the full pipeline.
- Test environment isolation: `monkeypatch.delenv("DPH_REGISTRY_PATH")` prevents host env vars from interfering with test registry paths.

### Changed
- All source and test files reformatted with ruff format.
- Import ordering normalized (isort).
- Minor code improvements: `pytest.raises(Exception)` → `pytest.raises(AttributeError)`, unused variable `d` → `_d`, explicit `strict=False` on `zip()`.

## [0.1.2] - 2026-04-13

### Changed
- Dispatcher now evaluates **all** matching entries per trigger (no short-circuit on first DENY). Governance semantics require full evidence, not fast veto. **Behavior shift for entry authors:** entries with non-idempotent side effects (file writes, network calls, counters) now run even after an upstream entry returns DENY. Audit existing entries for side-effect safety.
- Composer preserves per-entry metadata as `metadata["per_entry"][entry_id]` and joins deny/hint messages with `"; "`.
- Logger canonicalizes `warning` (alongside legacy `warn` alias).
- Registry pre-compiles `matcher` regex at load time.

### Added
- Single `dph_decision` JSONL record per dispatcher invocation: `trigger`, `matched_entries`, `per_entry_outcomes`, `final_decision`, `final_message`, `latency_ms`.
- Schema invariants with error codes: `E_DUPLICATE_ID`, `E_BAD_TIMEOUT`, `E_BAD_LOG_LEVEL`, `E_BAD_COMMAND`, `E_BAD_MATCHER`.

### Fixed
- `registry-schema.md` used `warn`; normalized to `warning` to match `cli.md` and runtime canonical level.
- `pyproject.toml` was stuck at `0.1.0` despite `plugin.json` being at `0.1.1`; all three metadata sources now agree.

## [0.1.1] - 2026-04-13

### Fixed
- Removed redundant `hooks` field from `plugin.json`; `hooks/hooks.json` is auto-loaded by Claude Code and the explicit reference caused a "Duplicate hooks file detected" error on plugin load.

### Changed
- Translated ASPICE engineering record (sys.1–3, swe.2) to English.

## [0.1.0] - 2026-04-13

### Added
- Initial release of `dynamic-prompt-harness` (dph).
- Core: `dispatcher`, `registry`, `executor`, `composer`, `logger`, `io_contract`, `schema`, `errors`.
- Claude Code adapter with `tool_response` → `tool_result` field mapping.
- Registry schema v1 with `id`, `triggers`, `command`, `matcher`, `priority`, `timeout_sec`, `log_level`.
- Per-entry env vars exposed to subprocesses: `DPH_ENTRY_ID`, `DPH_TRIGGER`, `DPH_LOG_LEVEL`.
- Dispatcher env overrides: `DPH_REGISTRY_PATH`, `DPH_LOG_PATH`.
- Fail-safe ALLOW at dispatcher level; fail-closed DENY at per-entry level (invalid JSON / timeout / non-zero exit).
- Diátaxis documentation (tutorial / how-to / reference / explanation).
- ASPICE engineering record (sys.1–3, swe.2).
- MIT license.
- 36 tests passing.

[0.1.0]: https://github.com/bibi-meow/dynamic-prompt-harness/releases/tag/v0.1.0
