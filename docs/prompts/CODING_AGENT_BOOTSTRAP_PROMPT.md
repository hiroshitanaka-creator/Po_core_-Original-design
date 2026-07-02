# Coding Agent Bootstrap Prompt（コピー用）

> このリポジトリで新しいコーディングエージェントセッションを開始するとき、
> セッション冒頭のプロンプトに以下をそのまま貼り付けて使うこと。
> 内容は `docs/AI_AGENT_INITIALIZATION_RULES.md` の要約版。

```
このリポジトリで作業を始める前に、以下を必ず読んでください：

1. docs/STRICT_CORE_RULES.md（概念保存 SSOT）
2. docs/original_design_status.md（ガバナンス層の現状）
3. docs/ARCHITECTURE_NORTH_STAR.md（アーキテクチャ目標）
4. docs/CONCEPT_DRIFT_GUARD.md（概念縮小防止チェック）
5. README.md
6. docs/厳格固定ルール.md, docs/status.md（運用・リリース面の単一真実）

Po_core は三層テンソル知性システムです：
- Po_core（テンソル基幹層）
- Po_self（再帰的自己再構成層）
- Viewer（外部共鳴・フィードバック層）

42人の哲学者は Po_core 内部の熟議モジュールであり、システムそのものではありません。

安全性は「床」であり「天井」ではありません。リスクのある機能は削除せず、
ゲート・閾値・トレーサビリティ・段階的実装・人間レビューを追加してください。

未実装の概念を勝手に削除しないでください。実装済み／計画中／概念のみ／研究仮説を
正直に区別してください（過大申告・過小申告のどちらも禁止）。

作業完了時は docs/original_design_status.md と CHANGELOG.md を更新し、
PR には Concept Preservation 節を含めてください。
```
