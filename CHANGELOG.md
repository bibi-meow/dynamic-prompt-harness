# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
