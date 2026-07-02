## Summary
- 変更概要:
- 背景/目的:

## Concept Preservation（Original Design ガバナンス層 — `docs/STRICT_CORE_RULES.md` 参照）
- [ ] Po_core tensor kernel preserved（Po_core テンソル基幹層を保存している）
- [ ] Po_self recursive layer preserved（Po_self 再帰層を保存している）
- [ ] Viewer feedback layer preserved（Viewer フィードバック層を保存している）
- [ ] 42 philosophers remain deliberation modules（42人の哲学者は熟議モジュールのままである）
- [ ] Safety used as floor, not concept ceiling（安全性を天井ではなく床として扱っている）
- [ ] Unimplemented concepts are labeled honestly instead of deleted（未実装概念を削除せず正直にラベル付けしている）

## Change Type
- [ ] Concept / SSOT
- [ ] Runtime behavior
- [ ] Trace / schema
- [ ] Documentation
- [ ] Governance
- [ ] Experiment

## 必須チェック（SSOT / 進捗 / テスト報告）
- [ ] SSOT `docs/厳格固定ルール.md` を読んだ
- [ ] `docs/status.md` を更新した（どこを動かしたかを記載）
- [ ] 実行したテストコマンドと結果を下記に記載した
- [ ] 影響範囲とロールバック手順を下記に記載した
- [ ] 既存の policy/golden/schema/migration チェック項目を削除していない（下位セクションで確認）

## 要件トレーサビリティ（M4ゲート）
- Requirement ID(s): REQ- / NFR- / FR-
  - [ ] 関連する要件IDを少なくとも1つ記載した
- 関連AT/シナリオ:
  - [ ] Acceptance Test ID / scenario を記載した（または「なし」と明記）

## Status Update
- 更新箇所（Completed / Meta / Next など）:
- 更新内容:

## Test Report
- [ ] `pytest -q`
- [ ] その他:

実行ログ（コマンドと結果）:
-

## Impact / Rollback
- 影響範囲:
- ロールバック手順:

## Policy Change Protocol v1（policy定数変更時のみ必須）
- [ ] policy定数変更なし（該当しない）
- [ ] policy_lab レポート（JSON）を添付した
- [ ] policy_lab レポート（Markdown）を添付した
- [ ] impacted_requirements 上位（例: Top 3）を本文へ記載した
- [ ] golden差分がある場合、再生成で更新した（手編集なし）
- [ ] golden差分要約（対象ケース/主要差分/妥当性）を本文へ記載した

## Evidence
- policy_lab artifacts:
  - JSON:
  - Markdown:
- impacted_requirements (Top):
  1.
  2.
  3.

## ADRチェック
- [ ] ADR不要（理由を記載）
- [ ] ADR追加/更新あり: `docs/adr/XXXX-*.md`

## ADR Requirement
Complete this section if the PR changes any of:
- SSOT / strict core rules
- architecture north star
- schema files
- trace contracts
- Po_core / Po_self / Viewer layer responsibilities
- concept drift rules
- governance rules
- future controlled modes: jump / reject / reactivate

- [ ] ADR required and added/updated: `docs/original_design_adr/ADR-####-*.md`
- [ ] ADR not required because:
- [ ] I ran `python scripts/check_adr_index.py`

## Determinism & Compatibility Checklist
- [ ] 凍結golden（`case_001` / `case_009`）を変更していない
- [ ] schema互換性を確認した（`tests/test_input_schema.py` / `tests/test_output_schema.py`）
- [ ] golden契約を確認した（`tests/test_golden_e2e.py`）
- [ ] 互換性に影響がある場合、`docs/operations/migration_guide_v1.md` を更新した

## Trace Continuity
Complete this section if the PR changes any of:
- `PoTraceEvent`
- trace event payloads
- `schemas/po_trace_event_v1.schema.json`
- `docs/contracts/PO_TRACE_EVENT_V1.md`
- `docs/contracts/TRACE_CONTINUITY_V1.md`
- Po_self decision events
- reconstruction planning/application events
- Viewer feedback trace events

- [ ] I ran `python scripts/validate_trace_continuity.py --include-negative`
- [ ] I ran `python -m pytest tests/test_trace_continuity_validator.py -v`
- [ ] I updated trace examples if event shape changed
- [ ] I updated trace contract docs if event semantics changed
- [ ] Not applicable because:

## Concept Drift Check
Complete this section if the PR changes README, PRD, architecture docs, governance docs, or public project wording.
- [ ] I ran `python scripts/check_concept_drift.py --check-pr-template`
- [ ] I confirmed this PR does not shrink Po_core into a generic chatbot, generic decision-support tool, safety wrapper, or philosopher roleplay system.
- [ ] Not applicable because:

## Notes
- 追加の注意事項・制約:
