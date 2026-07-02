# Concept Drift Guard

> 未来のAIエージェントが概念を縮小（drift）させることを防ぐためのチェックリスト。
> PR-010 より、このチェックリストは `scripts/check_concept_drift.py`（governance-only,
> ランタイム挙動への変更なし）によって機械的に強制される。ローカル実行・CI・失敗の読み方は
> `docs/operations/concept_drift_validation.md` を参照。以下の「悪い例」は
> concept-drift-ignore マーカーで囲み、検証器の誤検知対象から除外している（実例の意図的な保存であり、
> 抑制の濫用ではない）。

## ドリフトの兆候（Drift Smells）

以下のように聞こえる表現へ変化した場合、その変更は疑わしい：

- 普通のチャットボット
- 意思決定支援ラッパー
- 安全ゲート製品
- 多エージェント討論のおもちゃ
- 哲学者のロールプレイ
- 普通の説明可能AIダッシュボード

## PR前の必須チェック（Required Drift Check）

各 PR の前に以下へ回答すること：

1. この変更は Po_core / Po_self / Viewer の三層構造を保存しているか？
2. この変更は意味テンソル（semantic tensors）を保存しているか？
3. この変更は trace を自己再構成の基盤（substrate）として保存しているか？
4. この変更は Viewer をフィードバック層として保存しているか？
5. この変更は哲学者を「アイデンティティ」ではなく「モジュール」のまま維持しているか？
6. この変更は Safety Floor と Concept Ceiling を区別しているか？
7. この変更は未実装部分を正直にラベル付けしているか？

すべて「はい」でない場合、PR の Concept Preservation 節で理由を説明すること。

## 禁止される書き換え（Forbidden Rewrites）

悪い例：

<!-- concept-drift-ignore-start -->
> "Po_core is a safe philosophical decision-support chatbot."
<!-- concept-drift-ignore-end -->

良い例：

> "Po_core is a three-layer tensor intelligence system. Its current implementation may begin
> with decision support, but its architecture targets semantic responsibility processing,
> trace-based self-reconstruction, and viewer feedback loops."

## この Original Design リポジトリにおける具体例

`README.md` に既にある以下の記述は良い例として維持すること：

> "Po_core is a **three-layer tensor intelligence model** for processing the meaning and
> responsibility of speech. This is distinct from — and not to be confused with — the
> three-layer *safety gate* below."

一方で、以下のような単純化（縮小）は避けること：

> "Po_core は42人の哲学者が議論して安全な回答を出すシステムです。" <!-- concept-drift-ignore-line -->

哲学者による熟議は Po_core 基幹層の実装手段の一つであり、システムの定義そのものではない。
