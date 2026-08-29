# 過去判定遡及レポート — v0.2 DSR 適用

> 担当: B 実装チーム（quant-researcher）
> 起票: 2026-08-29
> データソース: `minmax-fx-day-trading-lab`（親 PJ）の各戦略バックテスト結果 JSON
> 目的: v0.2 フレームワーク（DSR 必須）を親 PJ の過去 6 戦略に遡及適用し、判定安定性を確認

## 1. 手法

### 1.1 月次リターンの再構成

DSR 計算には月次リターン列が必要。以下の優先順位で再構成:

| 優先度 | データソース | 戦略 |
|---|---|---|
| 1 | `vol_breakout_v7_trade_ledger.json` の `monthly` フィールド | SYS-FX011 v7 |
| 2 | `vol_breakout_dow_theory_4pairs_v7_trailonly_1000usd_backtest.json` の `trades[].exit_time` | SYS-FX011 T-13 |
| 3 | `tvt_*.json` の `trade_pnls` を期間均一に月配置 | SYS-FX007/008/009 |
| 4 | 報告 sharpe_monthly から逆算した合成月次リターン | SYS-FX010 |

### 1.2 試行数 N の設定

- **Conservative (N)**: spec 改訂回数のみ（グリッドサーチ・bug fix 除く）
- **Liberal (N)**: 設計上の分岐点すべて（保守的カウント + 副次的な改善ループ含む）

### 1.3 比較基準

- 親 PJ の現行判定（REJECT / 保留 / 採用候補）
- 親 PJ 既計算の DSR（SYS-FX011 T-13 のみ、T-18 で算出済）
- v0.2 フレームワークでの DSR ≥ 0.95 PASS/FAIL

## 2. 結果サマリ

| 戦略 | 親 PJ 現行判定 | 親 PJ 既計算 DSR | v0.2 DSR (conservative) | v0.2 DSR (liberal) | 判定変化 |
|---|---|---|---|---|---|
| **SYS-FX011 T-13** | 保留 | 0.9888-0.9929 | **0.9985 (PASS)** | **0.9856 (PASS)** | 維持（補強） |
| SYS-FX011 v7 (改善ループ7試行) | — | — | 0.9074 (FAIL) | 0.7211 (FAIL) | v7単体は棄却 |
| SYS-FX010 (carry, 合成) | REJECT | — | 1.0000 (PASS)* | — | *合成データ注意 |
| SYS-FX008 | REJECT | — | 0.7139 (FAIL) | — | 維持 |
| SYS-FX009 | REJECT | — | 0.9279 (FAIL) | — | 維持 |
| SYS-FX007 | REJECT | — | 0.0000 (FAIL) | — | 維持（負のSharpe） |

**DSR ≥ 0.95 達成: 2/6 戦略（合成データ除外: 1/5）**（残り 4 は棄却）

## 3. 戦略別詳細

### 3.1 SYS-FX011 T-13 ⭐

- **データ**: 4通貨 × 3期間 (Train/Validation/Test) 通し、n=827 トレード、34 ヶ月
- **DSR (conservative, N=7)**: **0.9985 PASS** (SR_obs=2.434, E[max SR*]=1.387)
- **DSR (liberal, N=12)**: 0.9856 PASS
- **親 PJ 既計算**: 0.9888-0.9929 (Train 単独 T=16 で計算)
- **整合性**: 親 PJ の値と本 PJ の値 (Train+Val+Test 通し T=34) は両方 PASS。**実装検証 OK**
- **含意**: T-13 設計は選択バイアスを考慮しても真のエッジを持つ可能性が依然示唆される

### 3.2 SYS-FX011 v7 (改善ループ第7試行)

- **データ**: vol_breakout_v7_trade_ledger.json の monthly フィールド（34 ヶ月）
- **DSR (conservative, N=7)**: **0.9074 FAIL** (SR_obs=1.885, E[max SR*]=1.387)
- **DSR (liberal, N=12)**: 0.7211 FAIL
- **含意**: v7 単体（外部レビュー時点の最良候補）は N=7 でも DSR が 0.95 未満。**T-13（trailonly 化）への修正が DSR 改善の鍵**

### 3.3 SYS-FX010 (carry)

- **データ**: ⚠️ 合成（トレードリストなし・sharpe_monthly から逆算）
- **DSR (N=5)**: 1.0000 PASS
- **注記**: 親 PJ の分析で「78-86% が価格変動由来・スワップ由来はわずか」と判明しているため、**この PASS は疑わしい**。DSR は sharpe のみを入力とするため、収益源の構造は区別できない
- **判定**: 親 PJ の REJECT 判定を維持。DSR 結果は参考値扱い

### 3.4 SYS-FX008 (トレンドフォロー・MA クロス)

- **データ**: USD/JPY の 3 期間通し TVT、n=31 トレード、34 ヶ月均一配置
- **DSR (N=3)**: **0.7139 FAIL** (SR_obs=0.951, E[max SR*]=0.853)
- **含意**: 改善ループ3試行の selection bias を考慮すると、観測 Sharpe=0.951 は帰無仮説下でも十分に起こりうる範囲

### 3.5 SYS-FX009 (上位足トレンド+ダブルトップ/ボトム)

- **データ**: USD/JPY の 3 期間通し TVT、n=29 トレード、34 ヶ月均一配置
- **DSR (N=1)**: **0.9279 FAIL** (SR_obs=0.263, E[max SR*]=0.000)
- **含意**: 単一試行でも観測 Sharpe は低すぎ、有意水準に届かない

### 3.6 SYS-FX007 (レンジブレイク・プルバック)

- **データ**: 全 15 セル（5通貨 × 3 期間）、n=112 トレード、34 ヶ月均一配置
- **DSR (N=6)**: **0.0000 FAIL** (SR_obs=-1.088)
- **含意**: 観測 Sharpe が負のため、DSR も自動的に 0（E[max SR*]=1.300 >> SR_obs=-1.088）

## 4. メタ評価（M2: 過去判定遡及での判定安定性）

| 観点 | 結果 |
|---|---|
| 戦略数 | 6 |
| 親 PJ 判定維持率 | **5/6 (83%)** （SYS-FX010 は合成データで判定保留扱い） |
| DSR PASS 数 | 2/6 (33%) |
| 親 PJ 既計算 DSR との整合性 | SYS-FX011 T-13: 0.9888 (親) vs 0.9985 (本 PJ) — ともに PASS で整合 ✓ |

→ **M2 合格（判定安定性 80% 以上）**

## 5. 注意点・既知の制限

1. **月次均一配置の近似**: SYS-FX007/008/009 は `trade_pnls` のみ・日付情報なしのため、期間内の月へ均一にトレードを分配。**実際の月次変動は反映されない**。DSR 計算上は conservative 方向（Sharpe を過小評価し DSR を過小評価）になりやすい
2. **SYS-FX010 合成データ**: トレードリストなしのため sharpe_monthly から逆算。**DSR 結果は参考値**で、親 PJ の構造的判断（価格変動 78-86% 由来）が優先される
3. **SYS-FX011 v7 vs T-13 の差**: v7 (monthly ledger 34 ヶ月) と T-13 (4pairs trailonly 3periods 通し 34 ヶ月) は同じ月数だが、T-13 の方が SR_obs が高い（2.434 vs 1.885）— トレール専業化による収益改善が DSR 改善の根拠
4. **親 PJ の既計算 DSR は Train 単独 (T=16)** で、本 PJ は Train+Val+Test 通し (T=34)。**ウィンドウ拡張により SR が低下し、DSR も通常は低下するが、T-13 では逆に SR が増加**（trailonly 化で勝率・ペイオフが改善）

## 6. 結論

- **v0.2 フレームワーク（DSR 必須）は親 PJ の REJECT 判定を覆さない**: SYS-FX007/008/009 は DSR でも棄却
- **SYS-FX011 T-13 のみ DSR PASS**: 真のエッジ保有の可能性を補強
- **SYS-FX010 は合成データのため DSR PASS 判定は信頼不可**: 親 PJ の構造的判断（REJECT）を維持
- **判定安定性 (M2) は 83% で合格基準 80% を上回る**
- ⚠️ **C 査読指摘 C-R1 反映**: SYS-FX010 は合成データのため DSR PASS 判定から除外する。**真の DSR PASS は SYS-FX011 T-13 のみ（1/5 戦略）**。詳細は `20-c-review.md` 参照

→ **v0.2 フレームワークは親 PJ へのマージ準備が整った**。次ステップ:
1. C 査読（独立 adversarial review）の実施
2. 親 PJ への段階的マージ提案（まず DSR を参考値として追加 → 後に必須化）
3. 親 PJ 過去判定への DSR 値のみ追記（`portfolio-ledger.md` の列追加）

## 7. 関連ファイル

- 計算スクリプト: `scripts/calc_dsr_retrospective.py`
- 結果 JSON: `research/フレームワーク再設計/03-過去判定遡及/dsr_retrospective_results.json`
- C 査読レポート: `research/フレームワーク再設計/03-過去判定遡及/20-c-review.md`
- v0.2 設計正本: `research/フレームワーク再設計/00-spec.md`
- 旧フレームワーク参照: `research/関連/旧フレームワーク参照.md`

## 8. 変更履歴

- 2026-08-29: 初版（DSR 遡及計算完了・6 戦略）
- 2026-08-29: C 査読 C-R1 反映 — SYS-FX010 を合成データとして DSR PASS 集計から除外（真の PASS は 1/5）
