# SYS.2 System Requirements Analysis: dynamic-prompt-harness

SYS.1（user-stories）から抽出した機能要件 / 非機能要件 / インターフェース要件 /
制約条件。v0.1 スコープ。

## 1. 機能要件（FR）

### 1.1 配布・初期化

| ID | 要件 | 由来 US |
|---|---|---|
| FR-001 | Claude Code plugin marketplace 経由で `/plugin install` による導入が可能 | A1 |
| FR-002 | slash command（`/dph-init`）により、カレントプロジェクトの `.claude/dynamic-prompt-harness/` 配下に `registry.json`（空/雛形）と `harnesses/` ディレクトリを生成する | A2 |
| FR-003 | plugin の `hooks.json` により dispatcher hook が PreToolUse / PostToolUse / UserPromptSubmit / PreCompact に自動登録される | A3 |

### 1.2 Dispatcher

| ID | 要件 | 由来 US |
|---|---|---|
| FR-010 | dispatcher は上記 4 トリガを単一エントリポイントで受信する | C1 |
| FR-011 | dispatcher は起動時に `.claude/dynamic-prompt-harness/registry.json` を読み込む | B1 |
| FR-012 | dispatcher は registry の各エントリを `trigger + tool + pattern` で粗フィルタし、合致したハーネスのみ subprocess 実行する | C2 |
| FR-013 | dispatcher は合致ハーネスを `priority` 昇順で実行する。同一 priority の場合は registry 登録順とする | C3, B3 |
| FR-014 | dispatcher はハーネス出力の `decision = deny` を検出した時点で後続ハーネスをスキップし、最終結果を `deny` として返す（短絡） | C3 |
| FR-015 | dispatcher は `decision = hint` のメッセージを全件連結して 1 つの出力にまとめる | C4 |
| FR-016 | dispatcher は個別ハーネスの異常終了（非ゼロ exit）/ 不正 JSON 出力を捕捉し、該当ハーネスをスキップして後続を継続する。ハング時の強制停止は行わず、Claude Code 側の hook timeout に委ねる | C5 |
| FR-017 | dispatcher は捕捉した異常をログに記録する（タイムスタンプ / session_id / trigger / ハーネス名 / 原因 / exit code） | C5 |
| FR-018 | dispatcher はログレベル（`debug` / `info` / `warn` / `error`）を環境変数 `DPH_LOG_LEVEL` または `registry.json` のトップレベル `log_level` で切り替えられる。既定は `info` | NFR-O |

### 1.3 Registry

| ID | 要件 | 由来 US |
|---|---|---|
| FR-020 | registry.json は JSON Schema で validate される。不正時はエラーメッセージを stderr に出力し dispatcher 起動を中止する | B4 |
| FR-021 | registry エントリは以下のフィールドを持つ: `name`（必須、一意）、`triggers`（必須、配列）、`tools`（任意、配列）、`pattern`（任意、regex 文字列）、`priority`（任意、整数、既定 100）、`enabled`（任意、bool、既定 true）。さらに `script` または `action` のいずれか一方を持つ（排他必須） | B1, B2, B3 |
| FR-021a | `action` フィールドは宣言的ハーネスを表現する。形式: `{"on_match": "deny" / "allow" / "hint", "message": "<文字列>"}`。dispatcher は subprocess を起動せず、pattern 一致時にこの結果を直接返す | B5（宣言的拡張） |
| FR-021b | `script` フィールドは独自実装ハーネスを表現する。形式: `.claude/dynamic-prompt-harness/harnesses/` 配下の相対パス。dispatcher は該当スクリプトを subprocess 実行する | B5 |
| FR-022 | `enabled: false` のエントリは dispatcher から無視される | B2 |

### 1.4 抽象化 I/O 契約

| ID | 要件 | 由来 US |
|---|---|---|
| FR-030 | ハーネスは stdin で抽象化入力 JSON を受け取る | B5, D2 |
| FR-031 | 抽象化入力は `trigger`, `tool`, `tool_input`, `context` フィールドを持つ。`context` には hook 経由でしか取得できないベンダ提供パラメータ（`session_id`, `cwd`, `transcript_path`, `hook_event_name` 等）を dispatcher がそのまま載せて渡す。ハーネスは `context.session_id` 等で参照可能 | D2 |
| FR-031a | dispatcher は Claude Code hook JSON の全フィールドのうち、抽象化 I/O に写像可能なものを `context` にパススルーする。ベンダ固有名（例: `hookSpecificOutput`）はそのままの名前でなく adapter が正規化した名前で格納する | D2, D3 |
| FR-032 | ハーネスは stdout に抽象化出力 JSON を返す。フィールドは `decision`（必須、`allow` / `deny` / `hint`）、`message`（任意）、`metadata`（任意、辞書） | B5 |
| FR-033 | ハーネス側では任意言語の実装が許容される（stdin/stdout 契約遵守が条件） | B5 |

### 1.5 Adapter

| ID | 要件 | 由来 US |
|---|---|---|
| FR-040 | Claude Code 固有の hook JSON（入出力）と抽象化 I/O の変換は adapter 層に閉じ込められる | C6, D1 |
| FR-041 | ベンダ固有拡張フィールド（Claude Code の `hookSpecificOutput` 等）は抽象化出力の `metadata` 経由で表現可能。adapter がベンダ固有フィールドにマッピングする | D3 |
| FR-042 | 将来のベンダ追加は `adapters/<vendor>.py` の新規追加で完結する設計とする（既存 core / ハーネスを変更しない） | D1 |

### 1.6 具象ハーネス動作（パターン表現可能性）

v0.1 スコープの 6 パターンが抽象化 I/O のみで表現可能であること。

| ID | パターン | 要件 | 由来 US |
|---|---|---|---|
| FR-050 | Gate | **宣言的で表現可能**。`action = {on_match: deny, message: ...}` | E1 |
| FR-051 | Guide | **宣言的で表現可能**。`action = {on_match: hint, message: ...}` | E2 |
| FR-052 | Validator | PostToolUse トリガ。単純ケースは宣言的、出力内容を動的に検査する場合は `script` | E3 |
| FR-053 | Guard | PreToolUse。前提条件が外部状態に依存しなければ宣言的、依存する場合は `script` | E4 |
| FR-054 | Circuit Breaker | カウンタ永続化が必要なため `script` 必須。ハーネス内で独自実装 | E5 |
| FR-055 | Monitor | PostToolUse で副作用のみ。ログ出力等はハーネス内実装が必要、原則 `script` | E6 |

### 1.7a 既存 hook との共存

| ID | 要件 | 由来 US |
|---|---|---|
| FR-070 | dispatcher は Claude Code の他 hook（ユーザが `settings.json` に登録済のもの）を参照・改変しない。独立したプロセスとして動作する | F1 |
| FR-071 | `registry.json` の `entries` が空 / 該当 trigger のエントリが 0 件の場合、dispatcher は ALLOW を返して正常終了する（exit code 0） | F4 |
| FR-072 | `priority` による実行順制御は dph 内ハーネスに閉じる。他 hook との順序は Claude Code の hook 仕様に従う。README / docs に明記する | F3 |
| FR-073 | 既存 hook から dph registry への段階的移行ガイドを docs として提供する（二重実行回避のため、移行済ロジックは `settings.json` から削除する手順を含む） | F2 |

### 1.7 state 管理方針

state 管理機能（DS/DE/RS/RC 等）はフレームワークの責務外とする。
Stateful Gate / Shield / Workflow 等 state 依存パターンが必要な場合、
利用者は `script` 型ハーネス内で独自に永続化層（ファイル / SQLite 等）を
実装する。framework は state 用の API / 拡張点を一切提供しない。

v0.1 / v0.2+ を通じて方針は不変とする。

## 2. 非機能要件（NFR）

### 2.1 性能

| ID | 要件 |
|---|---|
| NFR-P-001 | dispatcher の処理時間（hook 受信 → 結果返却）は合致ハーネスがない場合 100ms 以内（subprocess 起動コスト除く）を目標とする |
| NFR-P-002 | 宣言的ハーネス（`action`）は subprocess 起動なしで処理するため、script 型に比べ桁違いに高速であること |

### 2.2 信頼性

| ID | 要件 |
|---|---|
| NFR-R-001 | 1 個のハーネスが異常終了 / timeout しても、同一イベントの他ハーネス処理は継続する |
| NFR-R-002 | registry 読み込み失敗時は dispatcher を起動せず、Claude Code の hook をデフォルト（許可）で通過させる（fail-open）。fail-open の事実は stderr に記録する |

### 2.3 可搬性

| ID | 要件 |
|---|---|
| NFR-PT-001 | Windows / Linux / macOS で動作する |
| NFR-PT-002 | 実行には Python 3.9+ 標準ライブラリのみを使用する（外部依存ゼロ） |
| NFR-PT-003 | ハーネスコードはベンダ非依存。同一スクリプトが将来の別 vendor adapter 下でも動作する（抽象化 I/O 契約遵守が条件） |

### 2.4 拡張性

| ID | 要件 |
|---|---|
| NFR-E-001 | 新規ハーネス追加は、registry.json 編集 + scripts 配置のみで完結する（dispatcher / core コード変更不要） |
| NFR-E-002 | 新規 vendor adapter 追加は、`adapters/<vendor>.py` ファイル新規作成のみで完結する |
| NFR-E-003 | 宣言的ハーネス（`action`）により、script 不要の簡易ハーネスが registry 編集のみで追加できる |

### 2.5 保守性

| ID | 要件 |
|---|---|
| NFR-M-001 | 3 層構造（adapter / core / harness）が物理ディレクトリ上でも分離されている |
| NFR-M-002 | core コードはベンダ固有シンボルを import しない |

### 2.6 セキュリティ

| ID | 要件 |
|---|---|
| NFR-S-001 | dispatcher は registry.json で宣言されたスクリプトのみを起動する（任意パス実行なし） |
| NFR-S-002 | ハーネススクリプトのパスは `.claude/dynamic-prompt-harness/harnesses/` 配下に制限する（`../` トラバーサル禁止） |

### 2.7 観測性

| ID | 要件 |
|---|---|
| NFR-O-001 | dispatcher の実行ログ（タイムスタンプ / session_id / trigger / ハーネス名 / 結果 / エラー）は `.claude/dynamic-prompt-harness/logs/` に JSONL 形式で追記される |
| NFR-O-002 | ログレベルは `debug` / `info` / `warn` / `error` の 4 段階をサポートする（FR-018） |
| NFR-O-003 | ログローテーション / 保持期間は v0.1 では対象外（利用者責任） |

## 3. インターフェース要件（IR）

| ID | インターフェース | 仕様参照先 |
|---|---|---|
| IR-001 | Claude Code hook 入力 JSON | Claude Code 公式 hook spec |
| IR-002 | Claude Code hook 出力 JSON | Claude Code 公式 hook spec |
| IR-003 | 抽象化入力 JSON（dispatcher → harness） | FR-031 |
| IR-004 | 抽象化出力 JSON（harness → dispatcher） | FR-032 |
| IR-005 | registry.json スキーマ | FR-021 |
| IR-006 | plugin manifest `.claude-plugin/plugin.json` | Claude Code plugin spec |
| IR-007 | plugin hooks 登録 `hooks/hooks.json` | Claude Code plugin spec |

## 4. 制約条件（CON）

| ID | 制約 |
|---|---|
| CON-001 | v0.1 では state 管理機能を含まない（v0.2+ の別パッケージ扱い） |
| CON-002 | v0.1 では Claude Code adapter のみを提供する |
| CON-003 | dispatcher / adapter / core は Python 実装とする |
| CON-004 | 外部 Python 依存（requirements.txt 等）は導入しない |
| CON-005 | 配布は Claude Code plugin marketplace 形式とする |

## 5. トレーサビリティ

US → 要件の対応を以下に示す（逆方向トレースは各 FR 表の「由来 US」欄）。

| US | 対応 FR |
|---|---|
| US-A1 | FR-001 |
| US-A2 | FR-002 |
| US-A3 | FR-003 |
| US-B1 | FR-011, FR-021, NFR-E-001 |
| US-B2 | FR-021, FR-022 |
| US-B3 | FR-013, FR-021 |
| US-B4 | FR-020 |
| US-B5 | FR-030, FR-032, FR-033, FR-021b |
| US-B6 | FR-021, FR-021a, NFR-E-003 |
| US-C1 | FR-010 |
| US-C2 | FR-012 |
| US-C3 | FR-013, FR-014 |
| US-C4 | FR-015 |
| US-C5 | FR-016, FR-017, NFR-R-001 |
| US-C6 | FR-040 |
| US-D1 | FR-040, FR-042, NFR-M-002 |
| US-D2 | FR-030, FR-031, NFR-PT-003 |
| US-D3 | FR-041 |
| US-E1 | FR-050 |
| US-E2 | FR-051 |
| US-E3 | FR-052 |
| US-E4 | FR-053 |
| US-E5 | FR-054 |
| US-E6 | FR-055 |
| US-E7 | （framework 対象外 — 1.7 節、ハーネス内独自実装） |
| US-E8 | （framework 対象外 — 1.7 節、ハーネス内独自実装） |
| US-E9 | （framework 対象外 — 1.7 節、ハーネス内独自実装） |
| US-F1 | FR-070 |
| US-F2 | FR-073 |
| US-F3 | FR-072 |
| US-F4 | FR-071 |
