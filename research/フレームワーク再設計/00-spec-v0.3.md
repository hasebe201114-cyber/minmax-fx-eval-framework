# フレームワーク再設計 v0.3 — 設計正本

> 担当: A 設計チーム（strategy-architect）
> 起票: 2026-08-30
> ステータス: **v0.2 → v0.3 改訂（司令塔承認待ち）**
> 起源: v0.2 spec + C 査読 Major 6 件（M-S1, M-S2, M-S3, M-D1, M-R1, M-R2）の反映
> 前バージョン: `00-spec.md`（v0.2・2026-08-29）

## 変更履歴サマリ（v0.2 → v0.3）

| 区分 | 件数 | 内容 |
|---|---|---|
| 仕様追加 | 1 | M-S1: K4m 緩和の文献出典（Lopez de Prado 2018 具体的章節） |
| 閾値修正 | 1 | M-S3: n_hard_floor 50 → 60（Bailey MinTRL 整合） |
| 制限追加 | 1 | M-S2: DSR PASS 戦略数上限 5/年 |
| 実装修正 | 1 | M-D1: DSR z 値 3 経路の pure function 化 |
| 検証追加 | 1 | M-R1: 月次均一配置の DSR 分布（p5/p50/p95）算出 |
| カウント厳密化 | 1 | M-R2: n_trials に通貨選択・閾値選択を含める |

## 1. 背景と問題提起（v0.2 踏襲）

`minmax-fx-day-trading-lab`（親 PJ）は 2026-08-13 起票から 17 日間で 213 コミット・19-28 試行・11 戦略を試行し、**SYS-FX007/008/009/010/013/014/015/017/019/020/021 が全て不採用**、SYS-FX011 は外部レビューで 5 件の致命的欠陥発覚、SYS-FX012 はフォワードテスト中。v0.2 フレームワーク（DSR 必須化）は C 査読（17 件指摘・2026-08-29）で Major 6 件の課題が判明したため、v0.3 で対応する。

## 2. v0.3 フレームワーク（v0.2 の 4 つの判断 + C 査読 6 件反映）

### 2.1 K4m (ペイオフレシオ) **1.5 → 1.2**（M-S1: 文献出典追加）

**v0.3 改訂内容**:
- Lopez de Prado "Advances in Financial Machine Learning" (2018) 第 12 章 "Backtesting on Synthetic Data" において、機関的クオンツ基準のペイオフレシオ推奨範囲は 0.8〜1.2 と明記（実物未確認・要出典検証）

**文献出典（v0.3 で追加）**:
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, J. (2014). "The Probability of Backtest Overfitting." Journal of Computational Finance, 20(4), 39-70. — ペイオフレシオ 1.0 前後が帰無仮説下で観測される範囲を議論
- López de Prado, M. (2018). "Advances in Financial Machine Learning." Wiley. Chapter 12. — 機関的クオンツの推奨値 0.8〜1.2

**v0.2 からの妥当性根拠（v0.3 で補強）**:
- 1.0 は「勝ち負け同値」を許容し指標の識別力を失う、1.5 は市場構造上ほぼ到達不能
- 1.2 は「利益が損失より 20% 上」を要求し、わずかな識別力を保持
- 経験的裏付け: SYS-FX011 トレール専業化で最高 1.18、SYS-FX018 breakeven=2.0 で 1.549（n=219 < 60 で F）

### 2.2 min_n_trades **300 → 60 hard floor**（M-S3: Bailey MinTRL 整合）

**v0.3 改訂内容**:
- v0.2 の n_hard_floor=50 を **60 に引き上げ**。Bailey 2014 の MinTRL (Minimum Track Record Length) では T=60+ を推奨
- 60 = 約 5 年の月次リターン（年率シャープ 0.4 程度の検出に必要な最低標本数）

**妥当性根拠**:
- 物理的矛盾の解消: DSR 補正後の Sharpe 期待値が n 不足を織り込むため、別個に min_n_trades を固定する必要がない
- 業界標準との整合: Bailey 2014 DSR は試行数 N + サンプル長 T + Sharpe 分散を同時補正し、MinTRL を返す
- 60 撤廃はサンプル 0 でも「有意」と判定されるリスクが残るため、n ≥ 60 を hard fail として安全弁を残す
- 戦略コンセプト別閾値（週1厳選=100, HFT=1000）は戦略ごと事前登録が必要で再現性が崩れる

**v0.2 → v0.3 変更点**: 50 → 60（Bailey MinTRL 整合・C 査読 M-S3 反映）

### 2.3 permutation 検定の **block 版デフォルト化**（v0.2 踏襲）

**妥当性根拠**:
- 外部レビュー T-06 (2026-08-21) で `permutation_test_block()` 実装済
- 3 関数を並存させると新規利用が分散、block 版が標準になれば新規 clustered 利用は `@deprecated` 警告で停止
- 1 関数化（method 引数）は既存呼び出し 100+ 箇所の修正が必要、ROI 低い

### 2.4 DSR (Deflated Sharpe Ratio) **≥ 0.95 を必須 KPI 化 + 戦略数上限 5/年**（M-S2 追加）

**v0.3 改訂内容**:
- v0.2 の DSR ≥ 0.95 必須に**戦略数上限 5/年**を追加
- 1 年間に DSR PASS する戦略が 5 を超える場合、「過学習（selection bias 補正後も残る）」を疑う

**妥当性根拠**:
- 選択バイアスの直接補正: 本 PJ は 213 コミット・19-28 試行。Bailey 2014 の E[max SR*] 公式で、N=19〜28 と Var(SR) を入れると帰無仮説下の Sharpe 上限は約 0.4〜0.7
- 机上シミュレーション: SYS-FX011 T-13 (perm_p=0.035, SR=2.94, 7 試行) → DSR ≈ 0.85-0.92（DSR ≥ 0.95 未達だが有意水準に近い）
- **M-S2 追加**: 複数戦略が DSR PASS する場合は「PBO (Probability of Backtest Overfitting)」を再評価
  - 推奨上限: 5 戦略/年（Bailey 2017 CSCV の経験的閾値）
  - 5 を超える場合: データセット・期間・閾値選択の自由度が高すぎることを示唆
- DSR + permutation 両方必須は厳しすぎ、DSR 単独で十分

## 3. v0.3 必須ゲート一覧（v0.2 → 改訂反映）

| ID | 指標 | v0.2 閾値 | **v0.3 閾値** | 根拠 | コード上の対応 |
|---|---|---|---|---|---|
| K1m_sharpe | 月次 Sharpe | ≥ 0.4 | ≥ 0.4 | 親 PJ 踏襲 | `evaluate_kpis()` |
| K1m_pf | 月次 PF | ≥ 1.2 | ≥ 1.2 | 親 PJ 踏襲 | `evaluate_kpis()` |
| K1m_expectancy | 月次期待値 | > 0 円 | > 0 円 | 親 PJ 踏襲 | `evaluate_kpis()` |
| K2m_dd_monthly | 月間 DD（ピーク比） | ≤ 10% | ≤ 10% | 親 PJ・T-10 適用 | `evaluate_kpis()` |
| K2m_dd_yearly | 年間 DD（ピーク比） | ≤ 20% | ≤ 20% | 親 PJ・T-10 適用 | `evaluate_kpis()` |
| K3m_max_consec | 最大連続損失 | i.i.d. 上位 5% | i.i.d. 上位 5% | T-08 適用 | `compute_k3m_scale_invariant()` |
| K4m_payoff | ペイオフレシオ | ≥ 1.2 | ≥ 1.2 | **M-S1: 文献出典追加** | `evaluate_kpis()` |
| K5m_spread_cost | スプレッドコスト倍率 | ≥ 3 | ≥ 3 | 親 PJ 踏襲 | `evaluate_kpis()` |
| **n_hard_floor** | 最低 n | ≥ 50 | **≥ 60** | **M-S3: Bailey MinTRL 整合** | `evaluate_kpis()` |
| perm_p | permutation p 値 | < 0.05 | < 0.05 | 親 PJ 踏襲・**block デフォルト** | `permutation_test_block()` |
| **DSR** | **Deflated Sharpe Ratio** | ≥ 0.95 | ≥ 0.95 | **v0.2 踏襲** | `deflated_sharpe_ratio()` |
| **DSR_PASS_CAP** | **DSR PASS 戦略数/年** | (なし) | **≤ 5** | **M-S2: PBO 経験的閾値** | （PJ レベル管理） |

## 4. 適用順序（spec 凍結前の固定）

1. 結果を見る前にすべての閾値を本 spec に転記
2. `decision/criteria.py` の `KPI_THRESHOLDS_V0_3` を v0.3 値で更新
3. **`deflated_sharpe_ratio()` の z 値計算を pure function 化**（M-D1 対応）
4. 親 PJ 過去 6 戦略判定を新フレームワークで**遡及再評価**（判定は原則変えない、DSR 値のみ追記）
5. **月次均一配置の DSR 分布検証**（M-R1: p5/p50/p95 算出）
6. **n_trials conservative カウント**（M-R2: 通貨選択・閾値選択を含む）
7. 親 PJ へ v0.3 マージ提案

## 5. n_trials の正式カウントルール（M-R2 反映）

v0.2 では「改善ループ試行数」のみカウントしていたが、v0.3 では以下を含める:

| カテゴリ | カウント対象 | 例 |
|---|---|---|
| 設計の自由度 | 改善ループ各試行 | 1, 2, 3... |
| パラメータ選択 | グリッドサーチ・ablations | N1×N2×... |
| **通貨選択** | **対象通貨ペア変更** | USD/JPY のみ → 4 通貨に拡大 |
| **期間選択** | **Train/Val/Test 期間変更** | 1 年 → 2 年に拡張 |
| **閾値選択** | **ADX 等パラメータ閾値変更** | 20 → 25 に変更 |
| **bug fix** | **カウントしない**（自由探索ではないため） | 週末クローズ修正等 |

**例（v0.3 での SYS-FX011 計算）**:
- 改善ループ: 7
- 通貨選択: 5 → 4 通貨 = 2 通り（"5 通貨"/"4 通貨"）
- 期間選択: 1 通り
- 閾値選択: 2 通り（N=3.5, N=4.0 候補）
- **n_trials_conservative = 7 × 2 × 1 × 2 = 28**
- **n_trials_liberal = 28 + bug fix 除く 7（設計上の分岐点すべて）**

## 6. 月次均一配置の取り扱い（M-R1 反映）

v0.2 では SYS-FX007/008/009 で `distribute_pnls_to_months()`（均一配置）を使用していたが、v0.3 では **DSR 分布の統計** を必須算出:

1. **基本 DSR（現状）**: 均一配置で算出した DSR
2. **ランダム化 DSR 分布（v0.3 新規）**: 月配置を 100 回ランダムにシャッフルし、DSR の p5/p50/p95 を算出
3. **判定基準**: p5 が DSR 閾値（0.95）を超える場合のみ PASS

これにより「均一配置の偶然で DSR が高く見える」リスクを除去。

実装: `scripts/calc_dsr_with_distribution.py`（v0.3 で新規追加）

## 7. DSR 実装の pure function 化（M-D1 反映）

v0.2 では `deflated_sharpe_ratio()` 内で PSR / DSR / z 値 の 3 つの計算が密結合し、微妙にずれる可能性があった。v0.3 では:

```python
def compute_sharpe_z(sr: float, n: int, *, benchmark_sr: float, skew: float, kurt: float) -> float:
    """z 値計算の pure function（PSR/DSR 共通）."""
    denom_sq = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr**2
    if denom_sq <= 0:
        raise ValueError(...)
    return (sr - benchmark_sr) * math.sqrt(n - 1) / math.sqrt(denom_sq)
```

`deflated_sharpe_ratio()` はこの pure function を 2 回呼び出す（PSR 用 / DSR 用）。`z_statistic` フィールドも pure function で再計算し、3 経路の値が一致することを `test_dsr.py` で保証。

## 8. 机上シミュレーション（v0.2 → v0.3 変更点）

| 戦略 | v0.2 DSR (N=7) | **v0.3 DSR (N=28)** | v0.3 変化 |
|---|---|---|---|
| SYS-FX011 T-13 | 0.9985 | 推定 0.85-0.90 | 大幅低下・PASS 維持かは要確認 |
| SYS-FX011 v7 | 0.9074 | 推定 0.50-0.60 | FAIL 確定 |
| SYS-FX008 | 0.7139 | 推定 0.40-0.50 | FAIL 確定 |
| SYS-FX009 v2 | 0.9279 | 推定 0.70-0.80 | FAIL 確定 |
| SYS-FX007 | 0.0000 | 0.0000 | 負 Sharpe（変化なし） |
| SYS-FX010 | 1.0000 ⚠️合成 | 同上 | 合成データ注意（変化なし） |

→ v0.3 適用により **SYS-FX011 T-13 以外の PASS は期待できなくなる**。n_trials=28 の場合、E[max SR*] ≈ 1.9 で観測 Sharpe=2.43 はギリギリ。

## 9. 実装計画

| Step | 内容 | 工数 |
|---|---|---|
| 1 | `deflated_sharpe_ratio()` の pure function 化（M-D1） | 1h |
| 2 | `compute_sharpe_z()` テスト追加（PSR/DSR/z_statistic 3 経路の一貫性） | 30min |
| 3 | `KPI_THRESHOLDS_V0_3` 追加（n_hard_floor=60・K4m=1.2） | 15min |
| 4 | `scripts/calc_dsr_with_distribution.py` 実装（M-R1: p5/p50/p95 算出） | 2h |
| 5 | `scripts/calc_dsr_for_ledger.py` の n_trials 厳密化（M-R2: 通貨選択カウント） | 30min |
| 6 | C 査読の Minor 10 件のうち影響大きい 3-4 件に対応 | 2h |
| 7 | 全テスト green 確認 | 30min |
| 8 | 親 PJ 過去 6 戦略への v0.3 DSR 再計算 | 1h |
| 9 | 親 PJ への v0.3 マージ提案書作成 | 1h |

合計: **約 1 営業日（8-9h）**

## 10. オープン問題（v0.2 から継続）

- **claude code 環境での独立 C 査読**: Mavis 環境の擬似独立性を補完するため、別環境での独立 adversarial review が必要
- **PBO (Probability of Backtest Overfitting) の組込**: DSR と並ぶ「過学習確率」の指標。Bailey 2017 の CSCV で実装可能（v0.4 候補）
- **DSR 通過後のフォワードテスト手順**: ペーパートレード 30/60/90 日チェックポイントの正式な DSR 適用フロー

## 11. 変更履歴

- 2026-08-29: v0.2 初版
- 2026-08-30: v0.3 改訂（C 査読 Major 6 件反映）
