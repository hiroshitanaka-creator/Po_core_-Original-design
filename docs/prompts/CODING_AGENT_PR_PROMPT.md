# Coding Agent PR Prompt（コピー用）

> PR作成前にコーディングエージェントへ渡すチェック用プロンプト。
> `docs/CONCEPT_DRIFT_GUARD.md` の Required Drift Check に対応。

```
PRを作成する前に、以下の質問すべてに回答してください：

1. この変更は Po_core / Po_self / Viewer の三層構造を保存していますか？
2. この変更は意味テンソル（semantic tensors）を保存していますか？
3. この変更は trace を自己再構成の基盤として保存していますか？
4. この変更は Viewer をフィードバック層として保存していますか？
5. この変更は哲学者を「モジュール」のまま維持していますか（「アイデンティティ」化していませんか）？
6. この変更は Safety Floor と Concept Ceiling を区別していますか？
7. この変更は未実装部分を正直にラベル付けしていますか？

回答がすべて「はい」でない場合、PR本文の Concept Preservation 節に理由を明記してください。

PR本文には以下を含めてください（.github/PULL_REQUEST_TEMPLATE.md 参照）：

- Summary / Why / Scope
- Concept Preservation チェックリスト
- Change Type（Concept/SSOT, Runtime behavior, Trace/schema, Documentation, Governance, Experiment）
- Tests / Risks / Rollback
- STATUS / CHANGELOG 更新有無
```
