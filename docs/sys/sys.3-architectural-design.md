# SYS.3 System Architectural Design: dynamic-prompt-harness

SYS.2（system-requirements）で定義した FR/NFR/IR/CON を満たすアーキテクチャ。
v0.1 スコープ。モジュール構成 / データフロー / インターフェース / 配置の 4 軸で記述する。

## 1. アーキテクチャ原則

| ID | 原則 | 根拠 |
|---|---|---|
| AP-1 | 3 層分離（adapter / core / harness）を物理ディレクトリでも保つ | NFR-M-001 |
| AP-2 | `core` は `adapters` を import しない。adapter が core dataclass を参照する一方向依存 | NFR-M-002 |
| AP-3 | harness は subprocess 境界で core と接続。プロセス内参照を持たない | FR-030〜033 |
| AP-4 | dispatcher は hook 起動毎に新規プロセス。状態を持たない | CON-001, §1.7 |
| AP-5 | registry ロードは trigger 指定で絞り込んでから schema validate + filter | NFR-P-001 |
| AP-6 | ベンダ固有名は adapter 内で正規化し、core/harness には抽象名で渡す | NFR-PT-003 |

## 2. モジュール構成

### 2.1 リポジトリ / plugin レイアウト

```
dynamic-prompt-harness/                   # repo root = plugin root
├── .claude-plugin/
│   └── plugin.json                       # IR-006 plugin manifest
├── hooks/
│   └── hooks.json                        # IR-007 PreToolUse/PostToolUse/
│                                         #        UserPromptSubmit/PreCompact → dispatcher
├── src/dynamic_prompt_harness/
│   ├── __init__.py
│   ├── __main__.py                       # python -m dynamic_prompt_harness のエントリ
│   ├── dispatcher.py                     # オーケストレーション（後述 3.x）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── registry.py                   # load + JSON Schema validate + trigger/tool/pattern filter
│   │   ├── executor.py                   # declarative / script の実行
│   │   ├── composer.py                   # priority sort + DENY 短絡 + hint 連結
│   │   ├── io_contract.py                # AbstractInput / AbstractResult dataclass
│   │   ├── schema.py                     # registry.json JSON Schema 定義
│   │   └── logger.py                     # JSONL logger + log_level
│   └── adapters/
│       ├── __init__.py                   # 既定 adapter 選択（v0.1 は claude_code 固定）
│       └── claude_code.py                # parse_input / format_output の 2 関数
├── docs/sys/                             # SYS.1 / SYS.2 / SYS.3
└── README.md
```

### 2.2 ユーザデータレイアウト（対象プロジェクト側）

```
<project>/.claude/dynamic-prompt-harness/
├── registry.json                         # IR-005
├── harnesses/                            # script 型のみ配置
│   └── <name>.<任意拡張子>
└── logs/
    └── dispatcher.jsonl                  # NFR-O-001
```

### 2.3 依存方向

```
hooks/hooks.json  ──▶  dispatcher.py
                          │
                          ├──▶  adapters.claude_code   (parse_input / format_output)
                          │          │
                          │          └──▶  core.io_contract (dataclass のみ参照)
                          │
                          └──▶  core.{registry, executor, composer, logger}
                                       │
                                       └──▶  subprocess ──▶  <harness script>
```

`core` → `adapters` の矢印は存在しない（AP-2）。

## 3. Dispatcher 設計

### 3.1 エントリポイント

- Claude Code hook から `python -m dynamic_prompt_harness <trigger>` で起動（CON-003）
- `<trigger>` は `pre_tool_use` / `post_tool_use` / `user_prompt_submit` / `pre_compact` のいずれか
- stdin に Claude Code hook JSON、stdout に hook 出力 JSON

Python 直叩きとする理由: bash wrapper を挟むと OS 差分吸収点が 2 箇所に分かれる（sh/bat）。
Python に一本化すれば Windows / Linux / macOS を 1 経路で扱える（NFR-PT-001）。

### 3.2 処理シーケンス

```
1. __main__ が sys.argv[1] = trigger を取得
2. adapter.parse_input(stdin_json) → AbstractInput
      - vendor 固有キー（hookSpecificOutput 等）を正規化
      - context に session_id, cwd, transcript_path, hook_event_name を格納（FR-031, FR-031a）
3. registry.load(trigger)
      - registry.json 全件 → JSON Schema validate（FR-020）
      - triggers に <trigger> を含むエントリのみ返す（NFR-P-001 の一次絞り）
4. registry.filter(entries, AbstractInput)
      - tools / pattern で二次絞り（FR-012）
5. composer.sort(filtered)
      - priority 昇順 → 同 priority は registry 登録順（FR-013）
6. for entry in sorted:
      result = executor.run(entry, AbstractInput)
      results.append(result)
      logger.log(entry, result)
      if result.decision == DENY: break   # 短絡（FR-014）
7. final = composer.merge(results)
      - DENY があれば DENY（先勝ち。短絡済）
      - それ以外は hint を全件連結（FR-015）
      - どれも該当なければ ALLOW
8. adapter.format_output(final) → stdout JSON
```

### 3.3 エラー方針

| 事象 | 挙動 | 根拠 |
|---|---|---|
| registry.json が存在しない / 破損 | stderr にエラー記録、ALLOW を stdout に出して終了（fail-open） | NFR-R-002 |
| 個別 harness の非ゼロ exit / 不正 JSON | 該当結果をスキップしログ記録、後続継続 | FR-016, FR-017 |
| harness のハング | dispatcher は待つのみ。Claude Code hook の timeout に委ねる | FR-016 |
| adapter での JSON parse 失敗 | stderr 出力、ALLOW で終了 | NFR-R-002 |

## 4. Core モジュール詳細

### 4.1 `core.io_contract`

抽象化 I/O を dataclass として定義。JSON ↔ dataclass の変換はここに閉じる。

```python
@dataclass(frozen=True)
class AbstractInput:
    trigger: str            # "pre_tool_use" | "post_tool_use" | "user_prompt_submit" | "pre_compact"
    tool: str | None        # PreToolUse/PostToolUse 時のみ
    tool_input: dict        # tool 引数（PreToolUse/PostToolUse 時のみ非空）
    prompt: str | None      # UserPromptSubmit 時のみ
    context: dict           # session_id, cwd, transcript_path, hook_event_name, ...

@dataclass(frozen=True)
class AbstractResult:
    decision: str           # "allow" | "deny" | "hint"
    message: str | None
    metadata: dict          # vendor 固有拡張への写像用（FR-041）
```

### 4.2 `core.registry`

```python
def load(trigger: str, registry_path: Path) -> list[Entry]:
    """trigger に該当する enabled エントリのみ返す"""

def filter(entries: list[Entry], inp: AbstractInput) -> list[Entry]:
    """tools / pattern で二次絞り"""
```

- `Entry` は registry.json のエントリ 1 行を表す dataclass
- `script` / `action` は排他必須（schema でも validate、dataclass 化時にも assert）
- 登録順を保つため `list[Entry]` で扱う（dict 化しない）

### 4.3 `core.executor`

```python
def run(entry: Entry, inp: AbstractInput) -> AbstractResult:
    if entry.action is not None:
        return _run_declarative(entry, inp)
    else:
        return _run_script(entry, inp)
```

- `_run_declarative`: pattern は registry.filter で既にマッチ確認済 → `entry.action` を直接 AbstractResult に写す（subprocess 起動なし、NFR-P-002）
- `_run_script`:
  - `harnesses/` 配下のスクリプトを subprocess.run で起動
  - stdin = AbstractInput の JSON、stdout = AbstractResult の JSON
  - 非ゼロ exit / JSON parse 失敗は `AbstractResult(decision="allow", ..., metadata={"error": ...})` に変換（=スキップ扱い）
  - パスは `harnesses/` 配下に限定（`..` トラバーサル拒否、NFR-S-002）

### 4.4 `core.composer`

```python
def sort(entries: list[Entry]) -> list[Entry]:
    """priority 昇順、同 priority は入力順（stable sort）"""

def merge(results: list[AbstractResult]) -> AbstractResult:
    """DENY 先勝ち / hint 全連結 / どれもなければ ALLOW"""
```

### 4.5 `core.schema`

registry.json の JSON Schema（Draft 2020-12）を Python dict として保持。
`registry.load` が起動時に参照。外部依存を避けるため軽量な独自 validator か
`jsonschema` 相当を標準ライブラリだけで再実装（NFR-PT-002: stdlib only）。

### 4.6 `core.logger`

JSONL 追記。1 行 = 1 ハーネス実行イベント。

```json
{
  "ts": "2026-04-12T21:55:00+09:00",
  "session_id": "...",
  "trigger": "pre_tool_use",
  "harness": "block-env-file",
  "decision": "deny",
  "duration_ms": 12,
  "error": null
}
```

log_level の優先順: `DPH_LOG_LEVEL` env var > `registry.json.log_level` > 既定 `info`（FR-018）。

## 5. Adapter 層

### 5.1 `adapters.claude_code`

2 関数のみを公開（vendor 別に per-trigger メソッドは持たない — 複数 vendor を共通に扱うため）:

```python
def parse_input(raw: dict, trigger: str) -> AbstractInput:
    """Claude Code hook JSON → AbstractInput"""

def format_output(result: AbstractResult, trigger: str) -> dict:
    """AbstractResult → Claude Code hook JSON"""
```

### 5.2 正規化マッピング（v0.1）

| Claude Code hook フィールド | AbstractInput への格納先 |
|---|---|
| `session_id` | `context.session_id` |
| `cwd` | `context.cwd` |
| `transcript_path` | `context.transcript_path` |
| `hook_event_name` | `context.hook_event_name` |
| `tool_name` | `tool` |
| `tool_input` | `tool_input` |
| `prompt` | `prompt` |
| `hookSpecificOutput` | `context.hook_specific_output`（snake_case 正規化） |

出力側:

| AbstractResult | Claude Code hook JSON |
|---|---|
| `decision = "deny"` | `{"decision": "block", "reason": message}` |
| `decision = "hint"` | `{"hookSpecificOutput": {"additionalContext": message}}` 等、trigger 毎に適切な形へ |
| `decision = "allow"` | `{}`（空オブジェクト = 通過） |
| `metadata.*` | adapter が vendor 固有フィールドへ写像 |

trigger 毎の最終 JSON 形は Claude Code hook spec に依存するため、adapter 内に trigger → formatter のテーブルを持つ。これは vendor 固有実装詳細であり、core 層から見えない。

### 5.3 将来の vendor 追加

`adapters/<vendor>.py` に同じ 2 関数シグネチャで実装追加。
dispatcher の adapter 選択は `DPH_ADAPTER` env var を将来追加する拡張点として残す（v0.1 では claude_code 固定、CON-002）。

## 6. インターフェース定義

### 6.1 IR-005: registry.json スキーマ

```json
{
  "log_level": "info",
  "entries": [
    {
      "name": "block-env-add",
      "triggers": ["pre_tool_use"],
      "tools": ["Bash"],
      "pattern": "git\\s+add\\s+.*\\.env",
      "priority": 10,
      "enabled": true,
      "action": {
        "on_match": "deny",
        "message": ".env を git add するのは禁止。秘匿情報が漏れる可能性がある。"
      }
    },
    {
      "name": "post-commit-push-hint",
      "triggers": ["post_tool_use"],
      "tools": ["Bash"],
      "pattern": "git\\s+commit",
      "priority": 50,
      "enabled": true,
      "script": "post-commit-push-hint.py"
    }
  ]
}
```

排他制約: 各エントリは `action` か `script` のいずれか一方のみ（FR-021）。

### 6.2 IR-003: 抽象化入力 JSON（dispatcher → harness）

```json
{
  "trigger": "pre_tool_use",
  "tool": "Bash",
  "tool_input": { "command": "git add .env" },
  "prompt": null,
  "context": {
    "session_id": "abc123",
    "cwd": "/path/to/project",
    "transcript_path": "...",
    "hook_event_name": "PreToolUse"
  }
}
```

### 6.3 IR-004: 抽象化出力 JSON（harness → dispatcher）

```json
{
  "decision": "deny",
  "message": ".env ファイルの add は禁止",
  "metadata": {}
}
```

### 6.4 IR-006: plugin manifest

```json
{
  "name": "dynamic-prompt-harness",
  "version": "0.1.0",
  "description": "Hook-based dynamic prompt injection runtime",
  "author": "bibi-meow"
}
```

### 6.5 IR-007: hooks.json

```json
{
  "hooks": {
    "PreToolUse":       [{"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_tool_use"}]}],
    "PostToolUse":      [{"matcher": ".*", "hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness post_tool_use"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness user_prompt_submit"}]}],
    "PreCompact":       [{"hooks": [{"type": "command", "command": "python -m dynamic_prompt_harness pre_compact"}]}]
  }
}
```

## 7. データフロー全体図

```
Claude Code hook fires
        │
        ▼  stdin: vendor hook JSON
┌─────────────────────────────────────────────┐
│ python -m dynamic_prompt_harness <trigger>  │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ adapters.claude_code.parse_input     │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼  AbstractInput            │
│  ┌──────────────────────────────────────┐   │
│  │ core.registry.load(trigger)          │   │
│  │   → JSON Schema validate             │   │
│  │   → trigger で一次絞り               │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼  list[Entry]              │
│  ┌──────────────────────────────────────┐   │
│  │ core.registry.filter(tools, pattern) │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼                           │
│  ┌──────────────────────────────────────┐   │
│  │ core.composer.sort (priority+order)  │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼                           │
│  ┌──────────────────────────────────────┐   │
│  │ for entry in sorted:                 │   │
│  │   core.executor.run(entry, input)    │──────┐ subprocess (script 型のみ)
│  │   → AbstractResult                   │     ▼
│  │   logger.log(...)                    │   harness script
│  │   if DENY: break                     │   (stdin/stdout JSON)
│  └──────────────┬───────────────────────┘     │
│                 ▼  list[AbstractResult]   ◀───┘
│  ┌──────────────────────────────────────┐   │
│  │ core.composer.merge                  │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼  AbstractResult           │
│  ┌──────────────────────────────────────┐   │
│  │ adapters.claude_code.format_output   │   │
│  └──────────────┬───────────────────────┘   │
└─────────────────┼───────────────────────────┘
                  ▼  stdout: vendor hook JSON
           Claude Code 受信
```

## 8. 既存 hook との共存

dph は Claude Code の他 hook と独立したプロセスとして動作し、以下の前提で共存する（FR-070〜073, US-F1〜4）。

### 8.1 共存モデル

- Claude Code は trigger ごとに登録済 hook を全て起動する。dph dispatcher もその 1 つに過ぎない
- dph dispatcher は `settings.json` の他 hook 設定を読み書きしない
- 各 hook は独立プロセスのため stdout / 終了コード / exit 2（block）は干渉しない
- 最終判定は Claude Code の hook 合成モデルに従う（block が 1 つでもあれば block = AND 合成）

### 8.2 競合パターンと扱い

| # | パターン | dph の挙動 |
|---|---|---|
| 1 | 同一 trigger に user hook と dph が両方登録 | 両方独立実行。AND 合成 |
| 2 | 同一ロジックが user hook と dph 内ハーネスに重複 | 二重実行になる。移行ガイドで settings.json 側削除を推奨（FR-073） |
| 3 | user hook と dph 間の実行順 | dph の `priority` は dph 内限定。外部順は Claude Code 依存（FR-072） |
| 4 | user hook が exit 2、dph が JSON decision | 別経路なので干渉なし |
| 5 | PreCompact で user hook と dph が両方 block 判定 | AND 合成、両方通過必須 |

### 8.3 空 registry 時の挙動

`registry.json` の `entries` が空 / 該当 trigger のエントリが 0 件の場合、
dispatcher は subprocess を一切起動せず ALLOW を返して exit 0 する（FR-071）。
導入直後の空状態で既存機能を壊さない。

### 8.4 移行ガイド（docs として提供）

1. 既存 hook のロジックを 1 つずつ registry エントリ化（declarative で済むものは action、それ以外は script）
2. dph で動作確認
3. `settings.json` から該当 hook 行を削除
4. 二重実行がなくなったことをログで確認

## 9. 次ステップ

- クラス設計（dispatcher/registry/executor/composer/io_contract/adapter の関係・メソッドシグネチャ確定）
- TDD で `core.*` から実装（外部依存ゼロなので標準ライブラリの unittest で完結）
- `adapters.claude_code` は実 hook JSON サンプルに基づく契約テストを用意
- v0.1 リリース → Claude Code plugin marketplace 登録

## 10. トレーサビリティ（抜粋）

| FR/NFR | 実現モジュール |
|---|---|
| FR-010〜018 | `dispatcher.py` + `core.logger` |
| FR-020〜022 | `core.registry` + `core.schema` |
| FR-021a/b | `core.executor._run_declarative` / `_run_script` |
| FR-030〜033 | `core.io_contract` + subprocess 境界 |
| FR-040〜042 | `adapters/claude_code.py` |
| FR-050〜055 | registry entry 表現 + executor の 2 経路 |
| NFR-PT-002 | 標準ライブラリのみ、`core.schema` で JSON Schema validator 自作 |
| NFR-S-002 | `core.executor._run_script` でパス制限 |
| NFR-O-001 | `core.logger` JSONL 出力 |
| FR-070 | dispatcher は独立プロセス、他 hook を参照しない |
| FR-071 | `core.registry.load` が空配列を返した場合に executor をスキップし ALLOW 返却 |
| FR-072 | README / docs 記述（実行順仕様） |
| FR-073 | 移行ガイド docs（§8.4） |
