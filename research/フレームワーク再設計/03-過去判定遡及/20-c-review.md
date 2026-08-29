# C 査読レポート（Adversarial Review）— v0.2 フレームワーク

> 担当: C 品質チーム（adversarial-reviewer）
> 起票: 2026-08-29
> 査読対象:
>   1. v0.2 設計正本 (`research/フレームワーク再設計/00-spec.md`)
>   2. DSR 実装 (`src/minmax_fx_eval/statistics/dsr.py`)
>   3. DSR 遡及結果 (`research/フレームワーク再設計/03-過去判定遡及/dsr_retrospective_results.json` + REPORT.md)
> 性質: 独立 adversarial review（ただし **Mavis 環境制約** — 物理的に単一 LLM のため擬似独立。本制約は明示的に開示する）

## 0. 結論サマリ

| 対象 | 判定 | 重要指摘数 |
|---|---|---|
| v0.2 設計正本 | **条件付き承認** | Critical 0 / Major 3 / Minor 5 |
| DSR 実装 | **承認** | Critical 0 / Major 1 / Minor 2 |
| DSR 遡及結果 | **条件付き承認** | Critical 1 / Major 2 / Minor 3 |

→ **v0.2 フレームワークは親 PJ へのマージ準備が整ったが、C 査読で発見した 6 件の Major 指摘事項を反映すべき**。

## 1. 独立性に関する開示

Mavis 環境では物理的に単一 LLM のため、C 査読担当（adversarial-reviewer）は設計・実装担当者と同一モデル。Bailey 2014 の "Independent Review" の趣旨（独立思考からの盲点発見）は擬似的にしか達成できない。本制約は以下の影響を及ぼす:

- **影響 1**: 同じ訓練データ・同じ推論傾向により、v0.2 spec 設計者が見落とすのと同じ盲点を見落とす可能性
- **影響 2**: 設計の暗黙の前提（spec 執筆者の思考）を C 査読担当が完全には否定できない
- **緩和策**: 親 PJ へのマージ前に **claude code 環境での独立 adversarial review** を追加実施すべき

## 2. v0.2 設計正本への指摘

### 2.1 Major 指摘

#### M-S1: K4m 緩和 (1.5 → 1.2) の根拠に統計的裏付けが薄い

**問題**: spec §2.1 で K4m 1.2 緩和を「業界基準 0.8〜1.2 が標準」と根拠付けしているが、Bailey 2014 や Lopez de Prado の文献を直接引用していない。Lopez de Prado "Advances in Financial ML" 該当章を実物で確認していない。

**影響**: 司令塔が spec を承認する際、「なぜ 1.2 か」を外部査読で正当化できない。

**修正案**: spec §2.1 に Lopez de Prado 2018 の具体的章節引用を追加。最低でも "industry consensus 1.0-1.5" の出典を明示。

#### M-S2: DSR ≥ 0.95 必須化は「過去の判定を覆さない」と暗黙に仮定

**問題**: spec §5 机上シミュレーションで「v0.2 は過去判定の結果を覆さない」と結論しているが、これは **DSR 計算後の戦略のみ** で確認。**新規戦略** で DSR が PASS する見込みについては未評価。

**影響**: 新規戦略の「K4m 1.2 緩和で PASS する」というケースが出ない保証がない（DSR 通過後の戦略が複数生まれる可能性）。

**修正案**: spec に「DSR 通過 + K4m 1.2 PASS する戦略数の上限（推奨: 5 戦略/年）」を追加。PBO (Probability of Backtest Overfitting) との組み合わせを検討。

#### M-S3: n_hard_floor=50 の安全弁根拠が不明

**問題**: spec §2.2 で n_hard_floor=50 を「サンプル 0 でも有意と判定されるリスクへの安全弁」と位置付けるが、n=50 でも検出力は低い。Bailey 2014 の MinTRL (Minimum Track Record Length) では T=60+ を推奨。

**影響**: n=50 で DSR が PASS しても、t=16〜20 程度の月次リターンでは T-分布の裾で偽陽性リスクが残る。

**修正案**: n_hard_floor を 50 → 60 に引き上げるか、n=50 通過後に「DSR の z 値が 1.96 以上（片側 2.5%）」の追加チェックを要求。

### 2.2 Minor 指摘

#### m-S1: 「v0.1/v0.2 切替可能」API は内部混乱を生む可能性

evaluate_kpis() が `version: str` パラメータで両バージョンをサポートするが、これは v0.1 の REJECT 結果と v0.2 の GO 結果を同じコードで生成できることを意味する。**誤用のリスク**あり。

**修正案**: v0.1 は旧プロジェクト参照のみとし、新規呼び出しでは v0.2 のみを許可。`version` パラメータは deprecation 候補。

#### m-S2: skewness/kurtosis の NaN ハンドリング未定義

`deflated_sharpe_ratio()` で returns 配列に NaN が含まれる場合の挙動が未定義。`compute_metrics()` からの入力経路で発生しうる。

**修正案**: NaN/inf チェックを冒頭で追加。`ValueError("returns contains NaN/inf")` を送出。

#### m-S3: DSR_REQUIRED_THRESHOLD = 0.95 の根拠文献がコメントのみ

実装内のコメントに「Bailey 2014 標準」とあるのみで、原論文の具体的推奨値が引用されていない。

**修正案**: ソース論文 Table 1 / Figure 2 の具体的閾値をコメントに記載。

#### m-S4: permutation_test_clustered の非推奨化が不徹底

permutation.py の `permutation_test_clustered()` は `@deprecated` 警告のみで、削除されていない。新規利用者が警告を無視すれば使用可能。

**修正案**: v1.0 で clustered 版を完全削除。deprecated 期間中に利用者向け移行ガイドを提供。

#### m-S5: PJ000001 完了条件の判定基準が曖昧

PJ000001 §6「v0.2 all-pass 80% 以上の戦略で判定が維持」を「完了条件 (B)」としているが、**all-pass の数自体が DSR 緩和で増える**ため、数値が独り歩きするリスク。

**修正案**: 「all-pass 数」ではなく「判定維持率（KPI 個別ごと）」を完了条件にする。

## 3. DSR 実装への指摘

### 3.1 Major 指摘

#### M-D1: `deflated_sharpe_ratio()` の z 値計算が scipy 関数と微妙にずれる可能性

`deflated_sharpe_ratio()` 内部で `probabilistic_sharpe_ratio()` を 2 回呼び出し（PSR と DSR）、さらに別途 z 値を独自計算している。3 つの計算で z の定義が微妙に異なる:

- PSR の z: `(SR - 0) * sqrt(T-1) / sqrt(...)` with `skewness, kurtosis=0.0` デフォルト
- DSR の z: `(SR - E[max SR*]) * sqrt(T-1) / sqrt(...)`
- 独自計算の z: `deflated_sharpe_ratio()` 末尾で再計算

→ **3 つの z 値が微妙に異なる**。テストで検証されているのは `dsr` フィールドのみで、`z_statistic` フィールドの一貫性は未検証。

**影響**: レポート生成時に `z_statistic` を別ツールで利用する場合、計算経路に依存して値が変わる。

**修正案**: `z_statistic` を `psr/dsr` から逆算する pure function として分離。3 つの z 値が一致することを `test_dsr.py` で確認。

### 3.2 Minor 指摘

#### m-D1: `expected_max_sharpe_ratio(N=1)` がハードコードで 0 を返す

Bailey 2014 公式では N=1 で `Φ⁻¹(0) = -∞` だが、本実装は便宜的に 0 を返す。`N=1` の特別扱いがコメントで明示されていない。

**修正案**: docstring に「N=1 は PSR と同等（benchmark=0）」と明記。

#### m-D2: scipy.stats.kurtosis の fisher=True/False 引数の意味が依存

`deflated_sharpe_ratio()` で `fisher=False`（生 kurtosis）を使用しているが、Lopez de Prado の文献は fisher=True（超過 kurtosis）を使う例もある。**Bailey 2014 公式は生 kurtosis を使うので正しいが、混同リスク**あり。

**修正案**: docstring に「fisher=False（生 kurtosis、3 がガウス）」と明記。

## 4. DSR 遡及結果への指摘

### 4.1 Critical 指摘

#### C-R1: SYS-FX010 の DSR PASS は偽陽性

SYS-FX010 で DSR=1.0000 PASS と報告しているが、**月次リターンが合成データ**（sharpe_monthly から逆算）であり、実トレードデータではない。

**影響**: PASS 判定を「真のエッジの証拠」として読まれると誤った結論を導く。

**修正案**:
1. REPORT.md の SYS-FX010 結果を「参考値・合成」と明示（既に実施済）
2. `dsr_retrospective_results.json` でも `synthetic: true` フラグで除外
3. 最終サマリでも PASS 数の分母から SYS-FX010 を除外する（**DSR PASS: 1/5 (本物のみ)**）

**重要度**: Critical — このまま放置すると、C 査読を知らない読者（将来 PJ 引継ぎ担当）が「SYS-FX010 は DSR 通過」と誤読する可能性。

### 4.2 Major 指摘

#### M-R1: 月次均一配置の近似が conservative 方向のみとは限らない

`distribute_pnls_to_months()` は trade_pnls を期間内の月へ均一に分配するが、実際のトレード月は不明。**均一配置は偶然 sharpe を押し上げる方向に作用する可能性**（隣接月のプラスを集中させるケース）。

**影響**: SYS-FX008/009 の DSR は実データより高めに評価されている可能性。

**修正案**:
1. 月次配置のランダム化を 100 回行い、DSR の分布（p5, p50, p95）を報告
2. ワーストケース DSR を PASS/FAIL の判定基準にする
3. または、各トレードに実 exit_time を付加して再計算（可能な場合）

#### M-R2: n_trials のカウントが甘い

SYS-FX007 の n_trials=6 は「ablations 6 プリセット」のみカウント。SYS-FX008 の n_trials=3 は「改善ループ 3 試行」のみカウント。**しかし通貨 5 種の選択自体も自由パラメータ**であり、n_trials に加算すべき。

**影響**: n_trials が過小評価され、DSR が過大評価されている。

**修正案**:
- n_trials に「通貨選択」「期間選択」「閾値選択」を含めた conservative カウント
- 例: SYS-FX007 = 6 (ablations) × 5 (currencies) × 3 (periods) × ... = 数百オーダー → DSR はさらに下がる
- もしくは Bailey 2014 が推奨する conservative な N=100 で固定

### 4.3 Minor 指摘

#### m-R1: 「n_trials_conservative / n_trials_liberal」の二段階カウントが spec で未定義

REPORT.md では n_trials を 2 段階でカウントしているが、spec 00-spec.md にはこの区別の正式定義がない。**レポート生成のたびに n_trials カウントが変わるリスク**。

**修正案**: spec 00-spec.md に「n_trials の数え方」を正式定義（保守的 N / 自由 N の二段階）。

#### m-R2: DSR の `periods_per_year` が 12 (月次) で固定

`deflated_sharpe_ratio(returns, n_trials=N, periods_per_year=12)` で periods_per_year=12 を渡しているが、**日次・週次リターンが来た場合にどうするか**が未規定。

**修正案**: DSR 入力の正規化（必ず年率 Sharpe に揃える）を spec に明記。

#### m-R3: 結果 JSON の構造が spec 化されていない

`dsr_retrospective_results.json` の各 entry 構造は実装依存。将来の改善でフィールド名が変わると下流ツールが壊れる。

**修正案**: 結果 JSON の schema を spec に明示（type hints + example）。

## 5. 指摘のトリアージと対応

| 優先度 | 件数 | 対応方針 |
|---|---|---|
| Critical | 1 (C-R1) | **即修正**: レポート内の SYS-FX010 結果の表現を修正・最終サマリから除外 |
| Major | 6 (M-S1, M-S2, M-S3, M-D1, M-R1, M-R2) | spec v0.3 として 1 週間以内に修正 |
| Minor | 10 (m-S1〜m-S5, m-D1, m-D2, m-R1〜m-R3) | 必要に応じて spec v0.3 で対応 |

## 6. 判定（再掲）

- **v0.2 設計正本**: 条件付き承認（Major 3 件の修正を推奨）
- **DSR 実装**: 承認（Major 1 件の修正を推奨）
- **DSR 遡及結果**: 条件付き承認（Critical 1 件は即修正、Major 2 件は v0.3 で対応）

## 7. 親 PJ へのマージ提案への影響

Critical 1 件の修正（**SYS-FX010 を DSR PASS サマリから除外**）を反映すれば、以下のマージ提案が妥当:

1. **Phase 1 マージ（即時実行可）**:
   - DSR 関数を親 PJ に追加（参考値扱い）
   - `deflated_sharpe_ratio()` のみ。KPI 評価には組み込まない
   - 親 PJ 既存テストへの破壊的影響なし

2. **Phase 2 マージ（Major 反映後・1 週間後）**:
   - DSR を必須 KPI に追加（v0.2 完全適用）
   - 過去 6 戦略への DSR 値のみ遡及追記（判定は変えない）
   - 親 PJ の `portfolio-ledger.md` に DSR 列追加

3. **Phase 3 マージ（claude code 環境での独立 C 査読後）**:
   - 親 PJ への完全統合
   - 6 体のマルチエージェント体制での本格運用開始

## 8. オープン問題

- **claude code 環境での独立 C 査読**: Mavis 環境の擬似独立性を補完するため、別環境での独立 adversarial review が必要
- **DSR の N (試行数) の正式カウントルール**: 通貨選択・期間選択・閾値選択のどれを含むかを spec で明文化
- **PBO (Probability of Backtest Overfitting) の組込**: DSR と並ぶ「過学習確率」の指標。Bailey 2017 の CSCV (Combinatorially Symmetric Cross-Validation) で実装可能

## 9. 変更履歴

- 2026-08-29: v0.2 C 査読初版（Mavis 環境制約を明示開示）
