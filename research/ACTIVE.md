# ACTIVE - 進行状況の信号機

> 担当: E 進行チーム（archivist-pm）が更新する**機械的な進行状況**。
> 「今どの設計・実装が、誰の手にあり、次は誰待ちか」を 1 画面で表す。
> 戦略的な勝敗判断は `STRATEGY-BRIEF.md` を参照。

## 現在進行中の作業

| 作業 ID | テーマ | 担当 | ステップ | 状態 |
|---|---|---|---|---|
| FRW-001 | フレームワーク再設計 v0.2 spec 起票 | **A 設計チーム** | 起票完了・司令塔承認待ち | spec ドラフト完了（`research/フレームワーク再設計/00-spec.md`） |
| FRW-002 | DSR (Deflated Sharpe Ratio) 実装 | **B 実装チーム** | 雛形実装・テスト待ち | 雛形実装完了（`src/minmax_fx_eval/statistics/dsr.py`） |
| FRW-003 | permutation 検定の block デフォルト化 | **B 実装チーム** | 親 PJ からフォーク・clustered `@deprecated` 化 | 雛形実装完了（`src/minmax_fx_eval/statistics/permutation.py`） |
| FRW-004 | criteria.py の v0.2 閾値適用 | **B 実装チーム** | 雛形実装・K4m=1.2・n_hard_floor=50 | 雛形実装完了（`src/minmax_fx_eval/decision/criteria.py`） |
| FRW-005 | 親 PJ 過去 11 戦略への DSR 遡及計算 | **B 実装チーム** | 未着手 | spec 確定後に着手 |
| FRW-006 | C 査読（v0.2 spec への adversarial review） | **C 品質チーム** | 未着手 | spec 確定後に着手 |

## 直近の状態

- 2026-08-29: プロジェクト起票。`minmax-fx-day-trading-lab`（親 PJ）の評価フレームワーク部分を分離・独立 PJ 化
- 2026-08-29: v0.2 設計ドラフト完了。DSR 必須化・K4m 緩和（1.5→1.2）・n_hard_floor 導入・permutation block デフォルト化
- 2026-08-29: DSR 雛形実装完了（Bailey & Lopez de Prado 2014 公式の numpy 実装・scipy 依存のみ）
- 2026-08-29: permutation.py 雛形実装完了（親 PJ からフォーク・block デフォルト・clustered @deprecated）
- 2026-08-29: criteria.py 雛形実装完了（v0.2 閾値の反映のみ、評価ロジックは TODO）

## 司令塔への確認事項

| # | 質問 | 暫定デフォルト |
|---|---|---|
| Q1 | v0.2 設計 spec を承認するか | 承認想定 |
| Q2 | DSR 雛形実装（src/minmax_fx_eval/statistics/dsr.py）の単体テストを通過としたか | 通過想定 |
| Q3 | 親 PJ へのマージは spec 承認後すぐか、フォワードテスト結果（30/60/90日）後か | spec 承認後すぐを想定 |
