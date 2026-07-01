# Architecture North Star

> アーキテクチャ目標の高密度な定義。実装状況は本書ではなく
> [docs/STATUS.md](./STATUS.md) と [docs/status.md](./status.md) を参照すること。

## 一文で

Po_core は、語られたことを意味・責任・倫理的圧力・トレース・自己再構成・社会的フィードバック
として処理する三層テンソル知性システムである。

## 層構造

```
Viewer feedback
     ↓
Po_self controller
     ↓
Po_core tensor kernel / run_turn pipeline
     ↓
Po_trace / semantic_profile
     ↓
Po_self decision
     ↓
Final output
     ↓
Viewer resonance
```

## Layer 1: Po_core

責務：

- テンソルの計算
- 熟議モジュール（deliberation modules）の実行
- 安全ゲートの実行
- trace の発行
- 構造化された候補出力の生成

保存すべき概念テンソル：

- `semantic_delta`
- `ethics_delta`
- `responsibility_pressure`
- `freedom_pressure_tensor`
- `impact_field_tensor`
- `priority_score`
- `blocked_tensor`
- `shadow_tensor`（該当する場合）

現行実装との対応：既存の `run_turn` 10段階パイプライン
（`MemoryRead → TensorCompute → SolarWill → IntentionGate → PhilosopherSelect
→ PartyMachine → ParetoAggregate → ShadowPareto → ActionGate → MemoryWrite`）
および `src/po_core/tensors/` は、この Layer 1 の実装として扱う。

## Layer 2: Po_self

責務：

- `Po_trace` を読む
- `semantic_profile` を評価する
- 不連続性（discontinuity）を検出する
- 倫理的変動（ethical fluctuation）を検出する
- 判定する：
  - preserve（保持）
  - reconstruct（再構成）
  - jump（ジャンプ）
  - reject（拒否）
  - reactivate（再賦活）
- `max_self_cycles` により無制限の再帰を防止する

**注意（現状との区別）**：`src/po_core/po_self.py` の `PoSelf` クラスは、現時点では
`run_turn` パイプラインを呼び出す API ラッパーであり、上記の trace 観測・再帰判定ロジックを
実装したコントローラーではない。両者を混同しないこと（詳細は `docs/STATUS.md`）。

## Layer 3: Viewer

責務：

- 出力を受け取る
- 共鳴（resonance）を記録する
- 不同意（disagreement）を記録する
- 解釈の一致度（interpretation agreement）を記録する
- `feedback_tensor` を生成する
- フィードバックを Po_self へ返す

**注意（現状との区別）**：`src/po_core/viewer/` は現時点では観測可能性（observability）
ダッシュボード・可視化モジュール（pipeline view, tensor view, pressure display 等）であり、
上記の双方向フィードバックテンソルループを実装したものではない。両者を混同しないこと。

## 42人の哲学者

彼らは熟議モジュールである。彼らはシステムのアイデンティティではない。
彼らは視点、反論、統合、圧力信号を提供しうる。

## 安全性（Safety）

安全ゲートは実行を制約する。それらはアーキテクチャ全体を定義するものではない。
既存の三層安全ゲート（`IntentionGate` → `PolicyPrecheck` → `ActionGate`）は、
本書の三層テンソル知性モデルとは別の仕組みであり、混同してはならない
（`CLAUDE.md` の記載と同様）。
