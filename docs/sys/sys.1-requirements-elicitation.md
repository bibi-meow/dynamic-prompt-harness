# User Stories: dynamic-prompt-harness

Claude Code hook を利用した動的プロンプト注入 / ハーネスエンジニアリングの
汎用ランタイム。具象ハーネスを ad-hoc に追加できる仕組みを本体価値とし、
テンプレート提供は副次的とする。

## 前提（決定事項）

| 項目 | 決定 |
|---|---|
| リポ / plugin 名 | `dynamic-prompt-harness` |
| 追加単位 | 宣言的ハーネス（registry のみ）または 1 ハーネス = 1 スクリプト |
| Dispatcher | 単一 hook が全トリガ受ける |
| Registry | `registry.json` 中央集権 |
| I/O 契約 | 抽象化層あり（ベンダ非依存） |
| 合成 | 優先度＋短絡、同一 priority は登録順 |
| State | framework 対象外（必要時はハーネス内で独自実装） |
| 言語 | Python（dispatcher/adapter） |
| Matcher | 2 段階（registry 粗 + ハーネス細） |
| 配置（plugin） | `.claude/plugins/dynamic-prompt-harness/` |
| 配置（ユーザデータ） | `.claude/dynamic-prompt-harness/` |
| 配布 | Claude plugin + marketplace |
| v0.1 スコープ | dispatcher + registry + adapter のみ |

## ステークホルダ

- **プロジェクト運用者**: ランタイムを導入し registry を管理
- **ハーネス作成者**: 具象ハーネスを追加する
- **LLM エージェント**: 制御対象（hook で制約を受ける）
- **フレームワーク開発者**: dynamic-prompt-harness 本体を保守

## A. 導入・初期化

### US-A1
プロジェクト運用者として、`/plugin install dynamic-prompt-harness@<marketplace>`
でランタイムを導入でき、手動のファイル配置が不要。

### US-A2
プロジェクト運用者として、slash command（例: `/dph-init`）で
`.claude/dynamic-prompt-harness/` 骨子（registry.json + harnesses/）を
自プロジェクトに生成できる。

### US-A3
プロジェクト運用者として、インストール時に dispatcher hook が自動で
settings.json 相当に登録される（plugin の hooks.json 機構に依存）。

## B. ハーネス追加・更新

### US-B1
作成者として、スクリプトを `.claude/dynamic-prompt-harness/harnesses/` に
置き `registry.json` にエントリを追加するだけでハーネスが有効化される
（dispatcher コード改変不要）。

### US-B2
作成者として、registry の `enabled` フラグで個別ハーネスを無効化できる
（スクリプトは残したまま）。

### US-B3
作成者として、`priority` 整数で実行順を制御できる。
同一 priority の場合は `registry.json` での登録順で実行される。

### US-B4
作成者として、`registry.json` が schema 検証され、不正時は明確な
エラーメッセージが出る（無音で無視しない）。

### US-B5
作成者として、stdin/stdout 契約に従えば任意言語（bash / python / node 等）で
ハーネスを書ける。

### US-B6
作成者として、pattern hit → `deny` / `allow` / `hint` + 固定 message で済む
簡易ケースは、スクリプトを書かずに registry.json の宣言だけでハーネスを
追加できる（宣言的ハーネス）。

## C. 実行時挙動

### US-C1
フレームワークは PreToolUse / PostToolUse / UserPromptSubmit / PreCompact を
単一 dispatcher で受ける。

### US-C2
dispatcher は `trigger + tool + pattern` で subprocess 生成前に粗く絞り込む。

### US-C3
合致ハーネスを priority 順で実行する。同一 priority の場合は
`registry.json` の登録順。最初の DENY で短絡する。

### US-C4
HINT は全件連結して 1 つの出力にする。

### US-C5
個別ハーネスの timeout / crash は dispatcher が捕捉し、ログ出力 +
該当ハーネスのスキップ + 後続続行。

### US-C6
抽象化 I/O → ベンダ hook JSON の変換は adapter 層のみの責務。
core / ハーネスにベンダ固有コードは出現しない。

## D. ベンダ抽象

### US-D1
開発者として、Claude Code 固有ロジックは `adapters/claude_code.py` だけに
閉じ込められており、Cursor / Gemini 等の adapter 追加は新規ファイル作成で済む。

### US-D2
作成者として、ハーネスコードは vendor 非依存。同じスクリプトが別 vendor でも
動く（adapter が存在する前提）。

### US-D3
ベンダ固有機能（Claude Code の `hookSpecificOutput` 等）は adapter メタデータ
経由で表現可能。ハーネスコードにベンダ固有フィールドは漏れない。

## E. 具象ハーネス動作（パターン表現可能性の保証）

v0.1 で state 不要のパターン 6 件を US 化。
state 依存パターン 3 件は [v0.2+] として拡張点のみ担保。

### US-E1 — Gate
LLM が deny パターンに合う操作を試みると、推奨代替メッセージと共に
ブロックされる（例: `.env` ファイルの `git add`）。

### US-E2 — Guide
LLM がステップを完了すると、次ステップ HINT を受け取る
（例: commit 完了 → push 推奨）。

### US-E3 — Validator
LLM の出力がチェックに失敗すると、修正 HINT を受け取る
（例: 新規関数追加時に test ファイル欠如 → test 追加提案）。

### US-E4 — Guard
前提条件未充足時、充足手順付きでブロックされる
（例: `/compact` 実行時に日記未記入 → 日記 write 手順提示）。

### US-E5 — Circuit Breaker
同一エラーが N 回以上発生すると、後続同種操作をブロックし
人間エスカレートを HINT する。

### US-E6 — Monitor
PostToolUse で観測のみ（常に ALLOW、ログ出力）。
状態変更なしでメトリクス取得が可能。

### US-E7 — Stateful Gate（framework 対象外）
DS/DE 状態付き判定が必要な場合、ハーネス作成者は `script` 型ハーネス内で
独自の永続化層（ファイル / SQLite 等）を実装する。framework は state 管理
API を提供しない。

### US-E8 — Shield（framework 対象外）
使用中リソース保護が必要な場合も、同様にハーネス内独自実装。

### US-E9 — Workflow（framework 対象外）
多段ステップ遷移も、同様にハーネス内独自実装。

## F. 既存 hook との共存

### US-F1
プロジェクト運用者として、既に `settings.json` に登録済みの独自 hook を残した
まま dynamic-prompt-harness を導入でき、既存 hook が壊れない。dph は独立した
hook プロセスとして動作し、他 hook を参照・改変しない。

### US-F2
プロジェクト運用者として、既存 hook のロジックを段階的に registry に移行でき、
移行完了したものは `settings.json` 側から削除する運用で二重実行を回避できる
（移行ガイドがある）。

### US-F3
プロジェクト運用者として、dph の `priority` は dph 内ハーネスの順序のみを制御し、
他 hook との実行順は Claude Code の hook 仕様に従う、と明示的に理解できる。

### US-F4
プロジェクト運用者として、`registry.json` のエントリが 0 件の状態でも dispatcher は
ALLOW を返して正常終了する（導入直後の空状態で既存機能を壊さない）。

## 網羅性チェック

### ステークホルダ網羅
| ステークホルダ | 該当 US |
|---|---|
| プロジェクト運用者 | A1, A2, A3, F1, F2, F3, F4 |
| ハーネス作成者 | B1, B2, B3, B4, B5, B6, D2 |
| LLM エージェント | E1〜E9 |
| フレームワーク開発者 | C1〜C6, D1, D3 |

### カテゴリ別件数
- (A) 導入・初期化: 3
- (B) ハーネス追加・更新: 6
- (C) 実行時挙動: 6
- (D) ベンダ抽象: 3
- (E) 具象ハーネス動作: 9（うち framework スコープ 6、対象外 3）
- (F) 既存 hook との共存: 4

**framework スコープ US 合計: 28 件**（対象外 3 件は利用者責任として明記）
