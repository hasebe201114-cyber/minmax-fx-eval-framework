# v0.3 → 親 PJ マージ提案書（Phase 2）

> 担当: D デプロイチーム（integration-deploy）
> 起票: 2026-08-30
> マージ元: [`minmax-fx-eval-framework`](https://github.com/hasebe201114-cyber/minmax-fx-eval-framework) commit `95613b3`（v0.3 完成版）
> マージ先: [`minmax-fx-day-trading-lab`](https://github.com/hasebe201114-cyber/minmax-fx-day-trading-lab) main
> 目的: v0.3 フレームワーク（K4m=1.2・n_hard_floor=60・DSR 必須・DSR_PASS_CAP=5/年）を親 PJ に適用

## 1. 提案サマリ

| 項目 | 値 |
|---|---|
| Phase | **Phase 2**（DSR を必須 KPI に追加・v0.2/v0.3 完全適用） |
| Phase 1 からの継続 | 2026-08-29 DSR 関数追加（参考値扱い）→ 本提案で必須化 |
| 破壊的変更 | **あり**（KPI_THRESHOLDS の値変更・KPI 評価フローの更新） |
| 工数見積 | 4-6 時間 |
| リスク | 中（判定結果が変わる戦略あり） |

## 2. Phase 1 からの差分

| 項目 | Phase 1 (v0.2 参考値) | Phase 2 (v0.3 必須) |
|---|---|---|
| DSR 関数の利用 | 可能（参考値） | **必須ゲート化** |
| K4m 閾値 | 1.2（v0.2） | 1.2（v0.3・文献出典追加） |
| n_hard_floor | 50（v0.2） | **60（v0.3・Bailey MinTRL 整合）** |
| DSR PASS 戦略数上限 | なし | **5/年（v0.3 新設）** |
| n_trials カウント | 改善ループのみ | **通貨選択・閾値選択を含む（v0.3）** |
| 月次配置の DSR 分布 | 検証なし | **p5/p50/p95 必須算出（v0.3）** |
| 既存の K1m〜K7m 評価 | 不変 | 不変（K4m・n_hard_floor のみ変更） |

## 3. 期待される判定結果の変化

v0.3 DSR 分布（M-R1 で 100 サンプル検証済）の結果:

| 戦略 | Phase 1 判定 | **v0.3 判定 (p5 ≥ 0.95)** | 変化 |
|---|---|---|---|
| **SYS-FX011 T-13** | 参考 PASS | **❌ FAIL** (p5=0.9085) | **本採用候補から脱落** (claude code 環境 C 査読 C-1 訂正) |
| SYS-FX011 v7 | 参考 FAIL | ❌ FAIL (DSR 0.9074) | 維持 |
| SYS-FX010 | 参考 (合成) | (合成データ注意) | 維持 |
| SYS-FX008 | 参考 FAIL | ❌ FAIL (p5=0.3476) | 維持（より明確に） |
| SYS-FX009 v2 | 参考 FAIL | ❌ FAIL (p5=0.8997) | 維持 |
| SYS-FX007 | 参考 FAIL | ❌ FAIL (p5=0.0000) | 維持 |

→ **Phase 2 で判定が GO に変わる戦略は 0**。Phase 1 で保留だった SYS-FX011 T-13 も v0.3 厳格基準 (p5 ≥ 0.95) では **FAIL (p5=0.9085)**。2026-09-01 claude code 環境 C 査読 (C-1) により訂正 (旧記載「p5=0.9961 → PASS」は誤り)。**全 6 戦略が v0.3 DSR 分布テストで FAIL**。Phase 3 マージは Critical 3 件是正後に再検討。

## 4. マージ実装計画

### Step 1: 親 PJ への DSR 関連の追加（Phase 1 完了分・既にマージ済）

- [x] `src/minmax_fx_dt/statistics/dsr.py` 追加（v0.2）
- [x] `tests/test_dsr.py` 追加（v0.2・16 件）
- [x] `scripts/calc_dsr_for_ledger.py` 追加（v0.2）

### Step 2: v0.3 への update（Phase 2 で実施）

- [ ] `src/minmax_fx_dt/decision/criteria.py` の `KPI_THRESHOLDS` を v0.3 値に更新
  - K4m: 1.5 → 1.2（v0.2 と同値だが文献出典追加）
  - n_hard_floor: 50 → 60
- [ ] `KPI_THRESHOLDS_V0_3` を新規追加
- [ ] `evaluate_kpis()` の `version` パラメータに v0.3 対応
- [ ] `scripts/calc_dsr_for_ledger.py` の n_trials を M-R2 厳密カウントに更新
- [ ] `scripts/calc_dsr_with_distribution.py` を親 PJ にもコピー（M-R1）
- [ ] `tests/test_n_trials_counter.py` を親 PJ にも追加
- [ ] `tests/test_dsr.py` に v0.3 追加テスト（NaN handling・schema version）を反映
- [ ] `src/minmax_fx_dt/statistics/n_trials_counter.py` を親 PJ にも追加
- [ ] 親 PJ 過去 6 戦略への v0.3 DSR 再計算実行
- [ ] `portfolio-ledger.md` の DSR 列を v0.3 値で更新
- [ ] `CLAUDE.md` / `AGENTS.md` の DSR 説明を v0.3 に更新

### Step 3: 検証

- [ ] 全テスト green 化（親 PJ 既存 + 新規）
- [ ] 既存戦略判定の再現性確認（v0.2 と同じ結果が出ること）
- [ ] `portfolio-ledger.md` の差分レビュー
- [ ] `STRATEGY-BRIEF.md` の KPI 説明更新

## 5. リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| 既存テスト破壊 | 中 | 既存テストは v0.1/v0.2 互換を維持、v0.3 は別経路で追加 |
| 戦略判定の意図しない変化 | 中 | v0.3 適用前後で portfolio-ledger.md の差分レポート提出 |
| 性能劣化（v0.3 n_trials 厳密化・DSR 分布 100 サンプル） | 低 | DSR 分布はオンデマンド実行（CI では通常 skip） |
| 親 PJ の strategy-architect レビュー不足 | 中 | 本提案書で C 査読 17 件の対応を明示、Phase 3 で独立 C 査読 |

## 6. ロールバック計画

Phase 2 マージ後に問題が発生した場合:
1. 親 PJ で `git revert <commit>` でマージ取り消し
2. `decision/criteria.py` の `KPI_THRESHOLDS` を v0.2 値に戻す
3. `portfolio-ledger.md` の DSR 列を削除（参考値だった状態へ戻す）

ロールバック所要時間: 1 時間以内

## 7. 検証チェックリスト

- [ ] v0.3 適用後の全テスト green
- [ ] SYS-FX011 T-13 が **v0.3 厳格基準 (p5 ≥ 0.95) でも PASS** 維持 → **2026-09-01 訂正: FAIL (p5=0.9085)**, claude code 環境 C 査読 C-1 参照
- [ ] 過去 6 戦略の判定が v0.2 と一致（**v0.3 で GO に変わる戦略は 0 のはず**）
- [ ] C 査読 Major 6 件がすべて spec v0.3 に反映されている
- [ ] 親 PJ の既存評価フローが破壊されていない（評価対象 25+ 件すべて処理可能）
- [ ] `n_hard_floor=60` 未満の戦略が REJECT になる（n=42 以下の戦略を想定）

## 8. 関連ドキュメント

- v0.3 仕様書: `research/フレームワーク再設計/00-spec-v0.3.md`
- C 査読レポート: `research/フレームワーク再設計/03-過去判定遡及/20-c-review.md`
- DSR 遡及結果: `research/フレームワーク再設計/03-過去判定遡及/dsr_retrospective_results.json`
- DSR 分布結果: `research/フレームワーク再設計/02-比較/dsr_distribution_v03.json`
- Phase 1 マージ記録: `research/フレームワーク再設計/03-過去判定遡及/PHASE1_MERGE_RECORD.md`
- 親 PJ Phase 1 マージ: `minmax-fx-day-trading-lab` commit `3790ab8`

## 9. 推奨タイムライン

| 日付 | 作業 |
|---|---|
| 2026-08-30 | 本提案書レビュー（司令塔判断待ち） |
| 2026-08-31 | Step 2 実装（4-6h） |
| 2026-09-01 | 検証・テスト green 化 |
| 2026-09-02 | 親 PJ へ PR・マージ |
| 2026-09-02 〜 | Phase 3（claude code 環境での独立 C 査読） |

## 10. 変更履歴

- 2026-08-30: v0.3 完成に伴う Phase 2 マージ提案書初版
