# Claude Code Instructions

このプロジェクトは **FX 戦略評価のための統計的フレームワーク（KPI 定義・検定・複数試行補正）を設計・実装・検証する** 「minmax-fx-eval-framework」プロジェクトです。

「minmax」は minmax チーム（ユーザー）のクオンツ検証プロジェクト群の**共通識別子プレフィクス**で、GitHub リポジトリ名は `minmax-<topic>` の形式（例: `minmax-trading-pilot`, `minmax-fx-day-trading-lab`, `minmax-fx-eval-framework`）で揃える。

`minmax-fx-day-trading-lab`（FX バックテスト・戦略検証の親 PJ）の **評価フレームワーク部分**を抜き出して独立 PJ 化した姉妹プロジェクト。親 PJ の戦略試行サイクルを止めずに、評価装置の改善を独立に進めるために分離。

## 開発言語 / フレームワーク

**Python 3.11+ エコシステム**で構築（**親 PJ `minmax-fx-day-trading-lab` の評価系コードから派生**）。

主要依存:
- **数値計算**: `numpy`, `scipy`
- **データ**: `pandas`
- **検定**: `scipy.stats`（skewness, kurtosis, norm.ppf 等）
- **ログ**: `structlog`, `python-dotenv`
- **品質**: `pytest`, `ruff`, `mypy`, `black`（dev）

親 PJ からの流用資産（`src/minmax_fx_eval/` 配下）:
- `decision/criteria.py` — KPI 評価（K1m〜K7m + DSR 必須ゲートへ拡張）
- `statistics/permutation.py` — `permutation_test_block()` をデフォルト化（旧 `permutation_test_clustered()` は `@deprecated`）
- `statistics/dsr.py` — **新規**: Bailey & Lopez de Prado 2014 の Deflated Sharpe Ratio 実装
- `backtest/metrics.py` — 親 PJ から必要な部分のみフォーク

## 開発の方針

- 日本語で回答する。途中で英語になることがあるため注意
- セキュリティを優先する
- **HARKing 防止**: 結果を見る前に評価基準を数値で固定（spec 先行）
- 既存実装と整合しない箇所があれば先にチェック
- 検証 → 評価 → 修正 → テスト → デバッグのサイクルを基本
- 「ブラウザで DevTools を開いて〜」のようなユーザー操作前提の指示は出さない
- スマホで操作することもあるため、CLI 操作の可逆性に注意

## 親 PJ との関係

- **親 PJ**: `minmax-fx-day-trading-lab`（FX 戦略開発・バックテスト・検証）
- **本 PJ**: 親 PJ の評価フレームワーク（KPI 閾値・検定手法・複数試行補正）を独立に設計・実装
- **本 PJ の成果物**が stable になった時点で親 PJ へマージ提案
  - 親 PJ の `src/minmax_fx_dt/decision/criteria.py` を本 PJ の実装で置換
  - 親 PJ の `src/minmax_fx_dt/backtest/permutation.py` を本 PJ の実装で置換
  - 親 PJ の過去 11 戦略判定を新フレームワークで遡及再評価

## スコープ

**In Scope**:
- KPI 閾値の導出と正当化（K1m〜K7m の各閾値が業界標準・経験的根拠に基づき設定されていることの検証）
- 統計検定の手法選定と実装（permutation test、DSR、block bootstrap、Bonferroni/Holm 補正）
- 複数試行補正（Deflated Sharpe Ratio、Probability of Backtest Overfitting via CSCV）
- 親 PJ の戦略に対する遡及的評価（新フレームワークで再判定）
- フレームワークの比較検証（v0.1 vs v0.2、旧 vs 新）

**Out of Scope**:
- 新しい取引戦略の考案（親 PJ のスコープ）
- バックテストエンジンの実装（親 PJ の `simulator.py` を流用）
- ブローカー API 接続（親 PJ の `gmo_fx_client.py` を流用）
- フォワードテストの実行（親 PJ 側で実行・本 PJ では評価のみ）

## マルチエージェント体制

`minmax-fx-day-trading-lab` で確立した 6 体のマルチエージェント体制を踏襲:

- **S 戦略チーム (chief-strategist)**: フレームワーク設計の戦略判断・評価基準の優先順位付け
- **A 設計チーム (strategy-architect)**: KPI 閾値・検定手法の spec 確定。試算前に数値で固定
- **B 実装チーム (quant-researcher)**: spec に忠実に実装。評価関数・検定関数の生データ出力
- **C 品質チーム (adversarial-reviewer)**: フレームワーク自体が選択バイアス・HARKing を孕んでいないか検証
- **D デプロイチーム (integration-deploy)**: 親 PJ へのマージ・段階的展開
- **E 進行チーム (archivist-pm)**: ACTIVE 更新・obs 整理・親 PJ との同期

採用判断の権限は人間（司令塔 = ユーザー）に属する。本 PJ における「採用可」は「親 PJ へのマージ提案の是非」を意味し、本 PJ 単独の GO とは別。

## 検証フレームワークの判定基準（本 PJ 自身のメタ評価）

本 PJ の成果物（フレームワーク）が有効であるかを評価するための **メタ KPI**:

- **M1**: フレームワークがカバーするエッジ（K4m 構造的不可能性・permutation 検出力・DSR 必須化）の数
- **M2**: 親 PJ の過去 11 戦略に対する遡及評価で、判定が**変化しない**割合（後方互換性の確認）
  - 期待値: 80% 以上の戦略で判定が維持される（フレームワークの連続性）
- **M3**: フレームワークの実装行数 / ドキュメント行数 比（コードが説明的であることの指標）
  - 期待値: 0.3〜0.7（コードより説明が多い状態が理想）
- **M4**: C 査読の独立性確保（`Mavis 環境では物理的に同一 LLM となる制約` を明示的に開示）
