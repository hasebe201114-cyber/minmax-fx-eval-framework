# AGENTS.md

このプロジェクト（`minmax-fx-eval-framework`）の作業を開始する AI エージェント（Claude / Mavis / OpenCode 等）は、以下を順守すること。

## 必読

セッション開始時に**必ず**以下の順で読むこと：

1. `CLAUDE.md`（プロジェクト規約・スコープ・マルチエージェント体制）
2. `obs/minmax_fx_eval_framework/引き継ぎ/01進行中/` の最新引き継ぎノート
3. `research/ACTIVE.md`（機械的進行信号機）
4. `research/STRATEGY-BRIEF.md`（フレームワーク設計の戦略選定根拠）
5. `research/フレームワーク再設計/00-spec.md`（設計正本・v0.2）
6. `research/関連/旧フレームワーク参照.md`（親 PJ との対応表）

## 重要ルール

- **HARKing 防止**: 評価基準・閾値・判定式は spec で**結果を見る前に**数値固定
- **B 実装 / C 品質は別エージェント**で実行（同じ実装者が自分の結果を評価しない）
- **親 PJ へのマージ提案 GO は司令塔（ユーザー）の明示判断**
- **API キー / `.env.local` は読まない**。シークレットはコミットしない
- **日本語で回答**。途中英語になる場合は注意
- **マルチエージェント体制**: 6体（chief-strategist / strategy-architect / quant-researcher / adversarial-reviewer / integration-deploy / archivist-pm）。Mavis 環境では物理的実行は単一 LLM のため、叩き台・並列実行・Web 検索・ファイル操作を中心に活用。本番品質検証は claude code 環境へ

## ディレクトリ規約

- `research/フレームワーク再設計/`
  - `00-spec.md`（設計正本）
  - `01-エビデンス/`（KPI 閾値・検定手法の根拠データ・論文・ログ）
  - `02-比較/`（v0.1 vs v0.2 のシミュレーション結果）
  - `03-過去判定遡及/`（親 PJ の 11 戦略への遡及適用）
- `research/関連/`
  - `旧フレームワーク参照.md`（親 PJ との対応表・差分）
- `src/minmax_fx_eval/`
  - `decision/criteria.py`（KPI 評価）
  - `statistics/permutation.py`（permutation test・block デフォルト）
  - `statistics/dsr.py`（Deflated Sharpe Ratio・Bailey & Lopez de Prado 2014）
  - `statistics/power.py`（検出力計算・min_n_trades 動的導出）
  - `backtest/metrics.py`（必要部分のみ親 PJ からフォーク）
- `obs/minmax_fx_eval_framework/`
  - `00プロジェクト方針/`（PJ000001〜）
  - `01開発アイデア/`（着想・参考文献）
  - `70対応待ち/`（TODO・待機中）
  - `引き継ぎ/01進行中/`（アクティブ）
  - `引き継ぎ/02済み/`（過去）

## 変更履歴
- 2026-08-29: 初版作成（`minmax-fx-day-trading-lab` から評価フレームワーク部分を分離・独立 PJ 化）
