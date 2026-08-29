# Phase 1 マージ記録（2026-08-29）

## マージ概要

| 項目 | 値 |
|---|---|
| Phase | **Phase 1**（参考値追加・破壊的変更なし） |
| マージ元 | `minmax-fx-eval-framework` v0.2（[commit `8e104c8`](https://github.com/hasebe201114-cyber/minmax-fx-eval-framework)） |
| マージ先 | [`minmax-fx-day-trading-lab`](https://github.com/hasebe201114-cyber/minmax-fx-day-trading-lab) commit `3790ab8` |
| 司令塔承認 | Q1（v0.2 spec 承認）+ Q2（Phase 1 GO） |

## マージ内容

### 追加ファイル

| ファイル | 内容 |
|---|---|
| `src/minmax_fx_dt/statistics/dsr.py` | DSR 実装（Bailey & Lopez de Prado 2014・numpy/scipy） |
| `src/minmax_fx_dt/statistics/__init__.py` | モジュール公開 |
| `tests/test_dsr.py` | DSR 回帰テスト 16 件 |
| `scripts/calc_dsr_for_ledger.py` | 6 戦略の DSR 一括計算スクリプト |
| `research/method-notes/dsr_for_ledger.json` | 計算結果 JSON |

### 更新ファイル

| ファイル | 変更内容 |
|---|---|
| `research/portfolio-ledger.md` | 各戦略に DSR 列追加・2026-08-29 追記 |
| `CLAUDE.md` | 統計ライブラリに DSR 追加・流用資産に `statistics/dsr.py` 追加 |
| `AGENTS.md` | DSR 関数の扱い（参考値）を重要ルールに追加 |

## DSR 遡及結果（6 戦略）

| 戦略 | v0.2 DSR (N=conservative) | 判定 |
|---|---|---|
| **SYS-FX011 T-13** | **0.9985 PASS** ✅ | 親 PJ 0.9929 と整合 |
| SYS-FX011 v7 | 0.9074 FAIL | selection bias 補正で棄却 |
| SYS-FX010 | 1.0000 ⚠️合成 | C-R1 で除外扱い |
| SYS-FX008 | 0.7139 FAIL | 維持 |
| SYS-FX009 v2 | 0.9279 FAIL | 維持 |
| SYS-FX007 | 0.0000 FAIL | 負 Sharpe |

**判定結果への影響**: なし（参考値扱い・必須ゲート未組込）

## 検証

- **新規テスト**: 16/16 PASSED
- **既存テスト**: 75/75 PASSED（主要ユニットテスト）
- **回帰確認**: 既存 KPI 評価ロジックは変更なし・`decision/criteria.py` 不変

## Phase 2 / Phase 3 への布石

- **Phase 2 マージ**（Major 6 件修正後）: DSR を必須 KPI に追加・v0.2 完全適用
- **Phase 3 マージ**（claude code 環境での独立 C 査読後）: 親 PJ への完全統合・本格運用

## 関連コミット

- 親 PJ: `f1a25f5..3790ab8`（rebase 後 push）
- 新規 PJ 側: 変更なし（本記録は新規 PJ 側で Phase 1 完了マーク）
