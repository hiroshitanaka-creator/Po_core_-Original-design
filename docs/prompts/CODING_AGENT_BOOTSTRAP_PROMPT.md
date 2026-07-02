# Coding Agent Bootstrap Prompt（コピー用）

> このリポジトリで新しいコーディングエージェントセッションを開始するとき、
> セッション冒頭のプロンプトに以下をそのまま貼り付けて使うこと。
> 内容は `docs/AI_AGENT_INITIALIZATION_RULES.md` の要約版。
>
> PR-013 で `scripts/ai_agent_bootstrap_preflight.py --print-prompt` /
> `--write-prompt` が本ファイルをそのまま出力する。以下の日本語版
> （既存、変更なし）と、その下の英語版（PR-013 で追加）は同じ内容を指す
> 2つの表現であり、どちらを使ってもよい。

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

---

## English version (added by PR-013)

You are working in `hiroshitanaka-creator/Po_core_-Original-design`.

Before making changes, read:

1. `docs/STRICT_CORE_RULES.md`
2. `docs/AI_AGENT_INITIALIZATION_RULES.md`
3. `docs/ARCHITECTURE_NORTH_STAR.md`
4. `docs/CONCEPT_DRIFT_GUARD.md`
5. `docs/GOVERNANCE.md`
6. `docs/ROADMAP.md`
7. `docs/original_design_status.md`
8. `README.md`

Canonical identity:

Po_core is a three-layer tensor intelligence system for processing the
meaning and responsibility of speech.

- Po_core: tensor kernel
- Po_self: recursive trace-based self-reconstruction layer
- Viewer: external resonance / feedback tensor layer

The 42 philosophers are deliberation modules inside Po_core.
They are not the whole system.
Safety is a floor, not a concept ceiling.

Do not shrink Po_core into:

- a generic chatbot
- a generic decision-support tool
- a safety wrapper
- a philosopher roleplay system
- a simple multi-agent debate demo

If a feature is risky:

- add gates
- add thresholds
- add traceability
- add staged implementation
- add human review
- mark unimplemented parts honestly

Do not erase the concept.

Before opening a PR, run:

```bash
python scripts/ai_agent_bootstrap_preflight.py
```
