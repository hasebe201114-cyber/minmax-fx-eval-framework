# G タスク: claude code 環境 C 査読 — 投入プロンプト

> 担当: 司令塔 (Hasebe-san) が claude code 環境に貼付けて実行
> 起票: 2026-08-31
> 親 PJ 進捗: F (Phase 2 マージ) / H (C 査読 Minor 4 件) / I (p5 感度分析) 完了
> 残: G (本ファイル記載の独立 C 査読) のみ

## 0. 使い方

1. `claude code` を起動 (model: Sonnet 4.5 以上を推奨)
2. 以下の「投入プロンプト」セクション全文をコピー & ペースト
3. claude code の応答が完了したら `research/フレームワーク再設計/03-過去判定遡及/30-claudecode-c-review.md` にレポートが出力される
4. レポートを Mavis 環境に取り込み、Major / Critical 指摘に対応

---

## 投入プロンプト (claude code 環境にそのまま貼付け)

```markdown
# 独立 C 査読: v0.3 spec + Phase 2 マージ (真の adversarial review)

## あなたの役割

あなたは **C 品質チーム (adversarial-reviewer)** として、
`minmax-fx-eval-framework` v0.3 + 親 PJ `minmax-fx-day-trading-lab` への
**Phase 2 マージ結果** を**真の独立 adversarial review** します。

Mavis 環境 (別 AI セッション) では物理的に単一 LLM のため擬似独立の
C 査読が行われました。あなたは claude code 環境で動作する別モデルであり、
**真の独立思考** が期待されます。設計者・実装者・Mavis 環境査読者の盲点を
見つけることがミッションです。

## 査読対象 (3 つの単位)

### 対象 A: v0.3 spec 設計正本
- パス: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-eval-framework\research\フレームワーク再設計\00-spec-v0.3.md`
- 内容: DSR ≥ 0.95 必須化、K4m 1.2 緩和、n_hard_floor=60、DSR_PASS_CAP=5/年、
  M-R1 分布、M-R2 n_trials 厳密カウント、Minor 4 件 (m-S3, m-S4, m-S5, m-D1) 対応

### 対象 B: DSR 実装
- パス: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-eval-framework\src\minmax_fx_eval\statistics\dsr.py`
- パス: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-eval-framework\src\minmax_fx_eval\statistics\n_trials_counter.py`
- パス: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-eval-framework\src\minmax_fx_eval\statistics\permutation.py`
- 内容: Bailey 2014 公式の numpy 実装、M-D1 で抽出した compute_sharpe_z() pure function、
  n_trials 厳密カウント (conservative / liberal)、permutation_test_block デフォルト化

### 対象 C: Phase 2 マージコミット (親 PJ)
- 親 PJ: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-day-trading-lab`
- 主なコミット:
  - 10f4410: feat(eval): Phase 2 merge - v0.3 required gates
  - fed71a4: chore(eval): sync C 査読 Minor 4 fixes (m-S3, m-D1)
- 内容: `src/minmax_fx_dt/decision/criteria.py` (v0.1/v0.3 ディスパッチャ)、
  `scripts/calc_dsr_for_ledger.py` (6 ローダーが KNOWN_STRATEGY_N_TRIALS ベース)、
  `tests/test_n_trials_ledger_consistency.py` (16 リグレッションテスト)、
  `research/portfolio-ledger.md` (DSR 値更新)

## 既存 C 査読 (Mavis 環境) の参照

Mavis 環境での擬似独立 C 査読が既にあります:
- パス: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-eval-framework\research\フレームワーク再設計\03-過去判定遡及\20-c-review.md`
- 17 findings (Critical 1 / Major 6 / Minor 10) は v0.3 として全対応済み

これは「前段レビュー」と位置づけ、**あなたが発見する新規 findings** と
**既存 17 findings の対応の妥当性検証** の両方が求められます。

## 査読スコープ (Mavis 環境では擬似的にしか達成できなかった 5 つの軸)

### 1. v0.3 spec の前提・仮定の妥当性
- DSR ≥ 0.95 必須化: Lopez de Prado 2018 "Advances in Financial ML" §16.3 や
  Bailey 2014 本文での実際の推奨値は? 0.95 は強すぎる / 弱すぎる?
- K4m 1.2 緩和: 緩和の根拠に Lopez de Prado 該当章節の引用はあるか?
- n_hard_floor=60: 検出力計算の根拠は? 60 で十分か?
- DSR_PASS_CAP=5/年: PBO (Probability of Backtest Overfitting) との相互作用は?

### 2. DSR 実装の数値整合性
- compute_sharpe_z() pure function 抽出 (M-D1) は本当に
  PSR/DSR/z_statistic の 3 つの z 値を統一しているか?
- expected_max_sharpe_ratio(N=1) の特別扱いは数学的に妥当か?
- skewness/kurtosis の fisher=True/False 選択は Bailey 2014 公式に整合?
- deflated_sharpe_ratio() の NaN/inf ハンドリング (m-S2) は十分?

### 3. n_trials 厳密カウントの保守性
- 通貨選択 × 閾値選択 × 改善ループの積算は保守的過ぎないか?
- Mavis 環境 C 査読 M-R2 の修正案 "Bailey 2014 推奨 conservative な N=100 で固定" との比較
- 新規戦略が永久に PASS できないリスク (SYS-FX011 T-13 が p5=0.9085 で苦戦した事例)

### 4. DSR 分布の p5 閾値感度
- 現行 p5 ≥ 0.95 で 0 戦略通過という結果は妥当?
  サンプルサイズ不足・配置仮定のいずれの問題か?
- 段階ゲート化案 (p5 ≥ 0.90 で条件付き PASS + フォワードテスト併用) は妥当?
- p5 以外のロバスト性指標 (e.g. min, p1, p10) の検討

### 5. Phase 2 マージの運用上の落とし穴
- 親 PJ での v0.1 → v0.3 切替のデフォルト設計は適切?
- 後方互換のため v0.1 をデフォルトにしていることのリスクは?
- 既存 25+ テストケースが v0.3 で誤って PASS しないことの検証
- scripts/calc_dsr_for_ledger.py の n_trials フォールバック戦略 (_resolve_n_trials)
  は新 PJ と整合しているか?

## 期待する出力

**保存先**: `C:\Users\Atsushi Hasebe\.minimax-agent\projects\minmax-fx-eval-framework\research\フレームワーク再設計\03-過去判定遡及\30-claudecode-c-review.md`

**フォーマット**:
```markdown
# claude code 環境 C 査読レポート — v0.3 + Phase 2 マージ

> 担当: claude code 環境 C (真の独立 adversarial review)
> 起票: 2026-08-31
> 査読対象: v0.3 spec + Phase 2 マージコミット
>   - 親 PJ: 10f4410, fed71a4
>   - 新 PJ: 0cb6b05, 3fab90b, fc3d04b
> 性質: Mavis 環境とは異なるモデルによる真の独立査読

## 0. 結論サマリ

| 対象 | 判定 | 重要指摘数 |
|---|---|---|
| A. v0.3 spec | (条件付き承認/承認/差戻し) | Critical ? / Major ? / Minor ? |
| B. DSR 実装 | ... | Critical ? / Major ? / Minor ? |
| C. Phase 2 マージ | ... | Critical ? / Major ? / Minor ? |

→ 総合判定: (Phase 3 マージに進める / 修正後に再査読 / v0.4 として再設計)

## 1. 独立性に関する開示
(あなたが claude code 環境で動作することの独立性担保を 1 段落で述べる)

## 2. v0.3 spec への追加指摘
### 2.1 Critical 指摘
#### C-1: ... (具体的問題、影響、修正案)
### 2.2 Major 指摘
#### M-1: ...
### 2.3 Minor 指摘
#### m-1: ...

## 3. DSR 実装への追加指摘
(同様)

## 4. Phase 2 マージへの追加指摘
(同様)

## 5. Mavis 環境 C 査読 (20-c-review.md) 17 findings の妥当性再評価

| ID | Mavis 判定 | あなたの再評価 | 理由 |
|---|---|---|---|
| M-S1 (K4m 1.2 緩和) | Major | (同意/不同意) | ... |
| M-S2 (DSR_PASS_CAP) | Major | ... | ... |
| M-S3 (n_hard_floor=60) | Major | ... | ... |
| M-D1 (compute_sharpe_z 抽出) | Major | ... | ... |
| M-R1 (DSR 分布) | Major | ... | ... |
| M-R2 (n_trials 厳密カウント) | Major | ... | ... |
| C-R1 (SYS-FX010 合成データ) | Critical | ... | ... |
| m-S1〜m-S5, m-D1, m-D2, m-R1〜m-R3 | Minor | (各々) | ... |

## 6. 推奨アクション
- 即修正: ...
- v0.4 として再設計: ...
- 現状維持 (Phase 3 マージ可): ...

## 7. 変更履歴
- 2026-08-31: claude code 環境での真の独立 C 査読初版
```

## 査読の心構え

- **盲点を見つける**: Mavis 環境の擬似独立査読が「見落とすかもしれない」前提で動く
- **文献参照**: Bailey 2014 / Lopez de Prado 2018 該当章を実際に確認
- **数値検算**: テストの数値を自分で計算して一致するか
- **エラーケース**: 空配列、n_trials=0、無限大、負の sharpe などのエッジケース
- **監査証跡**: コードを読んだ第三者が判断根拠をトレースできるか
- **副作用**: v0.1 デフォルトに戻すと既存 25+ テストが壊れるリスク

## 既存 C 査読の取り扱い

Mavis 環境 C 査読 (20-c-review.md) の 17 findings は v0.3 として全対応済み。
あなたがやるべきは:
1. **Mavis 環境では見落とされた盲点の発見** (最重要 — 真の独立性の価値)
2. **17 findings の対応の妥当性検証** (Mavis 環境の自己評価を疑う)
3. **Phase 2 マージコミット固有の問題発見** (Mavis 環境査読時は未マージ)

## 完了条件

- 30-claudecode-c-review.md が作成されている
- 対象 A / B / C の 3 つすべてに判定が出ている
- 各指摘に Critical/Major/Minor の優先度が付いている
- 既存 Mavis 環境 C 査読 17 findings の再評価が §5 に含まれている
- 推奨アクションが明記されている (Phase 3 マージ可 / 修正必要 / v0.4 再設計)
```

---

## 期待される時間・労力

| 工程 | 想定時間 | 備考 |
|---|---|---|
| コードベース読み込み | 15-20 分 | spec 1 ファイル + 実装 3 ファイル + 親 PJ コミット 2 件 |
| 数値検算 | 15-20 分 | テストデータで DSR / E[max SR*] / z_statistic を手計算 |
| 文献参照 | 10-15 分 | Bailey 2014 / Lopez de Prado 2018 該当章を web 検索 |
| findings 整理 | 30-45 分 | 17 findings の再評価 + 新規 findings の発見 |
| レポート執筆 | 30-45 分 | 30-claudecode-c-review.md 出力 |
| **合計** | **約 2-3 時間** | claude code セッション 1 回で実施想定 |

## 想定される findings 候補 (Mavis 環境では手薄だった観点)

C 査読 (claude code 環境) で **より高精度** に検証されるべき盲点:

1. **DSR_REQUIRED_THRESHOLD = 0.95 の運用影響**
   - Lopez de Prado 2018 §16.3 では "DSR > 0.95" ではなく別の指標も提示
   - PBO との組み合わせで「5 戦略/年」制限は機能するか?

2. **n_trials 厳密カウントの境界ケース**
   - 「バグ修正」は n_trials に含めない (KNOWN_STRATEGY_N_TRIALS の n_bug_fixes 参照) が、
     統計的補正 (permutation 検定手法の是正等) との区別は妥当か?
   - SYS-FX008 の「週末クローズ修正」は「バグ修正」か「改善ループ」のどちらに数えるべきか?

3. **保守性カウント過剰の問題**
   - SYS-FX011 T-13 で n_trials=28 は、5 通貨 × 4 通貨 (実質 2 自由度) × 改善 7 × 閾値 2
     の積だが、実質的な独立な探索は 5 通貨から 4 通貨へ落とす「1 回」の選択のみ
   - 各自由度が本当に独立 (orthogonal) でない場合、積算は保守的過ぎる可能性

4. **DSR 分布のランダム化方法**
   - monthly placement のランダム化は「保守的な方向に振れる」とは限らない
     (Mavis 環境 C 査読 M-R1 で指摘済み)
   - p5 ではなく別の分位 (min, p1, p10) の方がロバストな指標の可能性

5. **Phase 2 マージのデフォルト設計**
   - 親 PJ の evaluate_kpis() で v0.1 をデフォルトにした判断は、
     「既存テストを保護」vs「v0.3 を誤って回避」のトレードオフ
   - 新規戦略で v0.3 必須ゲートを回避する抜け道がないか?

## 期待される findings 件数

- Mavis 環境 (擬似独立) で 17 findings
- claude code 環境 (真の独立) で **5-10 新規 findings** が典型的
- 既存 17 findings の半数程度は「再評価で別見解」となる可能性

## 投入後の確認

claude code 環境での作業完了後、以下を Mavis 環境で確認:
1. `research/フレームワーク再設計/03-過去判定遡及/30-claudecode-c-review.md` が存在するか
2. 重要指摘 (Critical / Major) が 0 件か少数か (大量にある場合は v0.4 再設計検討)
3. §5 の「17 findings の妥当性再評価」が埋まっているか
4. §6 の推奨アクションが明確か
