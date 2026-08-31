# claude code 環境 C 査読レポート — v0.3 + Phase 2 マージ

> 担当: claude code 環境 C (真の独立 adversarial review)
> 起票: 2026-08-31
> 査読対象: v0.3 spec + Phase 2 マージコミット
>   - 親 PJ: `10f4410`, `fed71a4`
>   - 新 PJ: `0cb6b05`, `3fab90b`, `1c5f39d`, `95613b3`, `fc3d04b`
> 性質: Mavis 環境とは異なるモデル・環境による真の独立査読（GitHub 上の実コミット・実データファイルを直接検証）

## 0. 結論サマリ

| 対象 | 判定 | 重要指摘数 |
|---|---|---|
| A. v0.3 spec | **差し戻し** | Critical 2 / Major 2 / Minor 1 |
| B. DSR 実装 | **条件付き承認**（`dsr.py` コメントの引用捏造を即修正すべき） | Critical 1 / Major 1 / Minor 1 |
| C. Phase 2 マージ | **差し戻し**（監査証跡の訂正必須。ロールバックは不要） | Critical 1 / Major 2 / Minor 0 |

→ 総合判定: **修正後に再査読**。特に「SYS-FX011 T-13 が v0.3 で PASS した」という Phase 2 マージの中核的な成果主張が、プロジェクト自身が生成したデータと矛盾しており（§2 C-1 参照）、公開済みの親 PJ マージコミットメッセージにまで誤情報が伝播している。ロールバックする実害（誤って採用された戦略）は無いが、**監査証跡（マージ提案書・コミットメッセージ）の訂正**が必須。

## 1. 独立性に関する開示

私は claude code 環境で動作する独立セッションであり、Mavis 環境（spec 設計・実装・自己査読を行った同一 LLM）とは別のモデルインスタンス・別の推論経路である。本査読では以下の手法で「盲点を見つける」という目的を具体的に果たした:

- v0.3 spec / dsr.py / merge proposal / 親 PJ 実コミット / JSON 生データを**すべて実際にコマンドで開いて突き合わせ**、文章の主張と生データの数値を直接比較した。
- 引用文献（Bailey & López de Prado 2014）を実際に PDF から取得し、テキスト抽出して「Table 1」「Figure 2」「§3.2 の推奨文」が実在するかを検索した。
- 親 PJ (`minmax-fx-day-trading-lab`) を読み取り専用で clone し、Phase 2 マージコミット（`10f4410`, `fed71a4`）の実際の diff とマージ後の `criteria.py` を検証した。

Mavis 環境の C 査読（20-c-review.md）は「同一 LLM による擬似独立」であるため、**設計者自身が正しいと信じ込んでいる前提**（特に文献引用の正確性、マージ提案書の数値の妥当性）を検証しないまま通過させるリスクがある。本査読ではまさにこの種の盲点を複数発見した（§2, §4）。

## 2. v0.3 spec への追加指摘

### 2.1 Critical 指摘

#### C-1: PHASE2_MERGE_PROPOSAL.md の中核主張「SYS-FX011 T-13 が v0.3 で PASS (p5=0.9961)」がプロジェクト自身のデータと矛盾する

**問題**: `research/フレームワーク再設計/PHASE2_MERGE_PROPOSAL.md` §3 は次のように記載する。

> | SYS-FX011 T-13 | 参考 PASS | ✅ PASS (p5=0.9961) | 本採用候補として維持 |
> → Phase 2 で判定が GO に変わる戦略は 0。Phase 1 で保留だった SYS-FX011 T-13 が v0.3 厳格基準でも維持される点が最大の価値。

しかし、この主張の根拠であるはずの M-R1 分布ファイル `research/フレームワーク再設計/02-比較/dsr_distribution_v03.json`（同じ v0.3 作業・同じ n_trials=28 で算出）を直接確認すると:

```json
{
  "sys_id": "SYS-FX011 T-13",
  "n_trials": 28,
  "dsr_baseline": 0.9138140832602071,
  "dsr_distribution": { "p5": 0.9084607839625524, "p50": 0.9941168857729354, ... },
  "passes_with_p5": false
}
```

**p5 の実値は 0.9085 であり、0.9961 という数値はリポジトリ内のどのデータファイルにも存在しない**（p50=0.9941 との混同、または誤記・捏造の可能性が高い）。p5≥0.95 の v0.3 必須ゲートで判定すると **SYS-FX011 T-13 は FAIL** — つまり Phase 2 マージが「唯一の成功例」として掲げていた戦略は、実際には v0.3 基準を通過していない。

さらに悪いことに、この誤った主張はドキュメントに留まらず、**実際に実行済みの親 PJ マージコミット** `10f4410` のコミットメッセージにまで伝播している:

```
Validation:
- SYS-FX011 T-13 only strategy to survive v0.3 (p5=0.9961 >= 0.95, M-R1 distribution)
```

**影響**: これは「監査証跡（audit trail）」の完全性に関わる Critical 事項。将来 PJ 引継ぎ担当者や司令塔がこのコミットメッセージ・マージ提案書のみを読めば、「v0.3 厳格基準でも 1 戦略は生き残った」という誤った成功体験を事実として受け取ってしまう。

**幸い実害は限定的**: 親 PJ の `portfolio-ledger.md`（2026-08-30 追記）は、別経路（`scripts/calc_dsr_for_ledger.py` の保守的 n_trials=28 での DSR ベースライン計算 = 0.8657）で独自に「❌ 保守 (n=28) で FAIL」と正しく結論しており、この誤った p5=0.9961 の値を採用判断には使っていない。ただし同じ追記の末尾で「新 PJ の M-R1 分布…は別途参照」として **PHASE2_MERGE_PROPOSAL.md（誤情報を含む文書）に判断を委ねる形で締めている**ため、今後この文書を参照した担当者が誤情報を信じるリスクは残る。

**修正案**:
1. `PHASE2_MERGE_PROPOSAL.md` §3 の SYS-FX011 T-13 行を「❌ FAIL (p5=0.9085)」に訂正し、「Phase 2 の価値」の説明文言（「T-13 が厳格基準でも維持される」）を撤回する。
2. 親 PJ に**訂正コミット**（`git revert` 不要。ロールバックすべき KPI 変更ではなく、ドキュメント記述の誤りなので、`portfolio-ledger.md` と履歴に「2026-08-31 訂正: p5=0.9961 は誤り、正しくは 0.9085 (FAIL)」を追記）を行う。
3. `dsr_p5_sensitivity_report.md`（Task I, 2026-08-30 生成、正しい p5=0.9085 を記載）との整合を明示的に取り、なぜ数値が食い違ったのか原因調査ログを残す。

#### C-2: 文献引用の内的不整合（章番号とタイトルの不一致）— 検証未完了のまま必須ゲートの根拠として採用

**問題**: `00-spec-v0.3.md` §2.1 (M-S1 対応箇所) は次のように記載する。

> Lopez de Prado "Advances in Financial Machine Learning" (2018) 第 12 章 "Backtesting on Synthetic Data" において、機関的クオンツ基準のペイオフレシオ推奨範囲は 0.8〜1.2 と明記（**実物未確認・要出典検証**）

**重大な点は、spec 自身が「実物未確認」と明記しているにもかかわらず**、Phase 2 マージのコミットメッセージ・PHASE2_MERGE_PROPOSAL.md では M-S1 が「対応済み」として扱われ、K4m=1.2 が親 PJ で**必須ゲート**として実装されていることである。未検証の引用を根拠に必須ゲートを追加するのは、まさに Mavis 環境の元の C 査読（M-S1）が指摘していた問題そのものであり、実質的に**未解決のまま「対応済み」とラベルされている**。

加えて、私の学習知識に基づく限り、"Advances in Financial Machine Learning" (2018) の目次では **第 13 章が "Backtesting on Synthetic Data"** であり、**第 12 章は "Backtesting through Cross-Validation"** である（バックテスト関連の章立て: Ch.11 The Dangers of Backtesting / Ch.12 Backtesting through Cross-Validation / Ch.13 Backtesting on Synthetic Data / Ch.14 Backtest Statistics / Ch.15 Understanding Strategy Risk / Ch.16 Machine Learning Asset Allocation）。「第12章」と「Backtesting on Synthetic Data」という組み合わせ自体が矛盾している可能性が高い。同様に `dsr.py` の `DSR_REQUIRED_THRESHOLD` コメントが引用する「Lopez de Prado 2018 §16.3」も、Ch.16 は "Machine Learning Asset Allocation" であり DSR/バックテスト統計の主題ではない章であるため、疑わしい。

**影響**: 必須ゲート（K4m=1.2, DSR≥0.95）という戦略の採否を直接左右する数値の正当化根拠が、検証されていない・章番号が疑わしい文献引用に依存している。これは HARKing 防止という本 PJ の存在意義（CLAUDE.md「結果を見る前に評価基準を数値で固定」）そのものを危うくする。

**修正案**:
1. 該当書籍・論文の実物（PDF/物理本）を直接参照し、章番号・該当ページ・実際の記述文言を確認する。
2. 検証が取れるまで、spec の該当箇所に「⚠️ 未検証」のフラグを維持し、**必須ゲート化を一時的に「参考値」へ格下げする**（Phase 1 相当に戻す）ことを検討する。
3. §7 の DSR 実装コメント（後述 B-1）も合わせて修正する。

### 2.2 Major 指摘

#### M-1: n_hard_floor=60 の「Bailey MinTRL 整合」根拠が誤帰属・誤引用

**問題**: spec §2.2 は「Bailey 2014 の MinTRL (Minimum Track Record Length) では T=60+ を推奨」と主張する。

実際に Bailey & López de Prado (2014) の DSR 論文原文（PDF から直接テキスト抽出して確認）を検証したところ:
- "Minimum Track Record Length" は論文冒頭の **Keywords 欄に単語として挙がっているのみ**で、本文中に MinTRL の定式化や具体的な推奨値（"60" 等）の記述は見当たらない。
- MinTRL の定式化は Bailey & López de Prado の**別の論文（2012年"The Sharpe Ratio Efficient Frontier", Journal of Risk）**が出典であり、しかもそこでの MinTRL は**固定の普遍定数ではなく**、目標 Sharpe・観測 Sharpe・歪度・尖度・信頼水準に依存する**戦略ごとの計算式**である。「T=60+ を推奨」という表現は、この可変な計算式を固定の閾値であるかのように誤って一般化している。

**影響**: n_hard_floor=60 という具体的な数値が、実際には検出力計算やシミュレーションではなく、誤帰属・簡略化された文献根拠のみに基づいている。M-S3（Mavis 環境）で指摘された「n_hard_floor=50 の安全弁根拠が不明」という問題は、60 に変更しても実質的に未解決のままである。

**修正案**: n_hard_floor の根拠を「Bailey 2014 MinTRL」という誤った帰属から切り離し、①検出力シミュレーション（帰無仮説下で年率Sharpe 0.4 を検出するのに必要な最小サンプル数を実際に計算する）、または②業界標準として単純に「5年の月次データ」という経験則、のいずれかとして正直に再記述する。

#### M-2: `dsr_p5_sensitivity_report.md`（Task I）の「案B: 閾値緩和で T-13 を救済」提案が本 PJ の HARKing 防止原則と自己矛盾

**問題**: v0.3 で p5≥0.95 を確定・親 PJ へマージ済みの**後**に実施された Task I（p5 感度分析、`dsr_p5_sensitivity_report.md`）は、4 戦略中 0 戦略が現行基準を通過するという結果を受けて、次を「推奨」している:

> **案 B**: p5 ≥ 0.95 → p5 ≥ 0.90 に緩和 (**SYS-FX011 T-13 を救済**)

「特定の戦略を救済するために結果を見た後で閾値を緩める」というのは、CLAUDE.md が明示的に禁止する HARKing（結果を見る前に評価基準を数値で固定する原則への違反）の典型例である。v0.3 の p5≥0.95 は spec 上「凍結された閾値」（spec §4「適用順序」①「結果を見る前にすべての閾値を本 spec に転記」）のはずであり、その後の分析でこれを緩和する提案自体が、フレームワークの目的と矛盾する。

**影響**: 提案が「参考情報」として書かれているだけで実際には採用されていない（現時点では p5≥0.95 のまま）ため実害はないが、この種の「閾値の後出しショッピング」提案がドキュメントとして正式に残ることは、将来の司令塔判断を歪めるリスクがある。

**修正案**: `dsr_p5_sensitivity_report.md` の「案B」に、HARKing リスクの明示的な警告を追記する。あるいは案Bを削除し、「事前登録済みの p5≥0.95 を変更する場合は、新しい独立した検証セット（今後の戦略）でのみ適用し、遡及適用しない」という運用ルールを明記する。

### 2.3 Minor 指摘

#### m-1: DSR_PASS_CAP=5/年 がコード上どこにも実装されていない

spec §2.4・§3 で「DSR_PASS_CAP ≤ 5」を必須ゲートの一覧に含めているが、実装は「（PJ レベル管理）」と明記され、コード上の強制チェックは存在しない（子 PJ `criteria.py` にも親 PJ `evaluate_kpis_v0_3()` のコメントにも "DSR_PASS_CAP 5/年 は PJ レベル管理（本関数では未実装）" と明記されている）。戦略数が今後累積した際、この上限を人手で毎回確認する運用は形骸化しやすい。

**修正案**: 最低限、`portfolio-ledger.md` を機械的に集計して年間 DSR PASS 数をカウントする簡易スクリプト（CI や定期実行でも可）を用意する。

## 3. DSR 実装への追加指摘

### 3.1 Critical 指摘

#### B-1: `dsr.py` の文献引用コメントが実在しない記述を引用している（捏造の疑い）

**問題**: `src/minmax_fx_eval/statistics/dsr.py` 51-58 行目のコメントは次の通り:

```python
# 出典: Bailey, M. N. & Lopez de Prado, M. (2014). ...
#   - Table 1 (p.96): "DSR p-value threshold" で 0.95 を "Strong evidence" として推奨
#   - Figure 2 (p.98): 0.95 を推奨ゲート閾値として図示
#   - §3.2 "Deflated Sharpe Ratio"  本文: "We recommend a minimum DSR of 0.95 for
#     a strategy to be considered statistically significant after multiple testing."
```

論文原本（`davidhbailey.com/dhbpapers/deflated-sharpe.pdf`）を実際に取得し、PDF テキストを抽出して該当箇所を検索したところ:

- 論文中の図表はすべて **"Exhibit 1"〜"Exhibit 4"** という名称で通しており、**"Table 1" や "Figure 2" という名称の図表は論文中に一つも存在しない**。
- 引用符付きで示されている文 **"We recommend a minimum DSR of 0.95 for a strategy to be considered statistically significant after multiple testing."** は、論文全文（47,909 文字を抽出・全文検索）のどこにも見つからない。
- 論文中で 0.95 という数値が現れる唯一の文脈は、p.16 付近の具体例（架空の investor/analyst のシナリオで「95% confidence level」という一般的な統計慣習を例示的に使っているのみ）であり、**論文が普遍的な「DSR≥0.95 を必須とすべき」という規範的推奨をしている箇所はない**。

**このコメントは、Mavis 環境 C 査読の m-S3（「原論文の具体的推奨値が引用されていない」）への対応として commit `fed71a4` で追加されたものだが、対応の過程で実在しない章・図表番号・引用文を作り出してしまっている**（いわゆる citation hallucination）。これはまさに「同一 LLM による自己査読では見抜けない」典型例であり、真の独立査読の価値を示す発見である。

**影響**: `DSR_REQUIRED_THRESHOLD = 0.95` という、戦略の採否を直接左右する必須ゲート値の文献的正当性が、実質的に無根拠になっている。コードコメントを読んだ第三者は「原論文に明記された基準」と誤認する。

**修正案**:
1. `dsr.py` のコメントから "Table 1 (p.96)"・"Figure 2 (p.98)"・引用符付きの推奨文を即座に削除する。
2. 0.95 という閾値は「一般的な統計的有意水準の慣習（95% 信頼水準）を DSR に適用した本 PJ 独自の設計判断」として正直に記載し直す。原論文はこの具体的な閾値を規範として推奨してはいない。
3. §2.1 C-2 と合わせ、`00-spec-v0.3.md` 側の "Lopez de Prado 2018 §16.3" 引用も同様に検証・修正する。

### 3.2 Major 指摘

#### B-2: `compute_sharpe_z()` の kurtosis 引数チェックが境界値で不完全

`compute_sharpe_z()` は `kurtosis < 1.0` で `ValueError`、`kurtosis < 1.5` で警告を出す。しかし実際の月次リターン系列で観測される尖度は、正規分布で raw kurtosis=3.0 が基準であり、`kurtosis < 1.5` という警告閾値は「fisher=True (超過尖度) との混同」を検出する意図（コメント参照）にしては境界が中途半端である（例えば真の生尖度が 1.6 の非正規分布は正当に存在しうるが、fisher=True で 1.6 を渡した場合との区別がこの閾値だけでは付かない）。実質的な誤用防止効果は限定的。

**修正案**: 呼び出し側 API に `kurtosis_convention: Literal["raw", "excess"]` のような明示的な引数を追加し、暗黙の閾値判定に頼らない設計に変更することを検討。

### 3.3 Minor 指摘

#### B-3: `permutation.py` の `PAIR_CORRELATION_MATRIX["GBP_JPY"]` に重複キーが残存

37 行目: `"GBP_JPY": {"USD_JPY": 0.7871, "GBP_JPY": 0.9183, "GBP_JPY": 1.0, "AUD_JPY": 0.8516, "EUR_USD": 0.0902}` — `"GBP_JPY"` キーが辞書リテラル内に 2 回出現し、Python の仕様上後勝ちで `1.0`（自己相関）が残り `0.9183` が黙って消える。コメントで「元コードtypo」と既知の問題として記載されているが未修正のまま残されている。

`effective_pair_count()` のループは `unique_pairs[i+1:]` で自己ペアを除外するため、**現状の呼び出しパターンでは実害はない**（自己相関 1.0 が参照されることはない）が、将来のリファクタで自己ペアを含む形に変更された場合に不正な値（0.9183 の代わりに 1.0）を静かに使ってしまうリスクがある。

**修正案**: 単純に重複キーを削除する（`"GBP_JPY": 0.9183` の 1 つだけ残す）。1 行の修正で済む。

## 4. Phase 2 マージへの追加指摘

### 4.1 Critical 指摘（§2.1 C-1 と同一事象、マージ実装への影響として再掲）

C-1（PHASE2_MERGE_PROPOSAL.md の誤った p5=0.9961 主張）は、実際に親 PJ の完了済みマージコミット `10f4410` のコミットメッセージにまで伝播済みである。§2.1 を参照。

### 4.2 Major 指摘

#### D-1: 子 PJ（本リポジトリ）自身の `criteria.py` が v0.3 を実装していない — 「v0.3 完成版」という表現と実態の乖離

**問題**: `PHASE2_MERGE_PROPOSAL.md` は「マージ元: `minmax-fx-eval-framework` commit `95613b3`（v0.3 完成版）」と明記し、v0.3 spec §4「適用順序」は「`decision/criteria.py` の `KPI_THRESHOLDS_V0_3` を v0.3 値で更新」を必須手順としている。

しかし本リポジトリの `src/minmax_fx_eval/decision/criteria.py` を実際に確認すると:

- `KPI_THRESHOLDS_V0_3` という定数は**存在しない**（`KPI_THRESHOLDS_V0_1` と `KPI_THRESHOLDS_V0_2` のみ）。
- `evaluate_kpis(stats, *, version: str = "v0.2")` の `version` 引数は `"v0.1"` と `"v0.2"` のみ受け付け、`"v0.3"` は未対応（渡すと `ValueError`）。
- `KPI_THRESHOLDS_V0_2["n_hard_floor"] = 50` のままで、spec が要求する 60 への更新が**子 PJ 側では反映されていない**。

つまり、v0.3 の実際の実装（K4m=1.2 は v0.2 の時点で既に反映済みだが、n_hard_floor=60・DSR_PASS_CAP・`KPI_THRESHOLDS_V0_3` は）は**親 PJ の `criteria.py` に直接追加されただけ**で、その"出どころ"であるはずの子 PJ には存在しない。「子 PJ で spec→実装→検証してから親へマージ提案する」という本 PJ の存在意義（CLAUDE.md「本 PJ の成果物が stable になった時点で親 PJ へマージ提案」）に反し、実質的に v0.3 のロジックは親 PJ 側で直接実装され、子 PJ は後追いで追いついていない状態にある。

**影響**: 子 PJ を「v0.3 の正本」として参照した場合、n_hard_floor=60 等の値を確認できず、将来の齟齬の火種になる。

**修正案**: `src/minmax_fx_eval/decision/criteria.py` に `KPI_THRESHOLDS_V0_3` と `evaluate_kpis_v0_3()`（またはそれに相当する dispatch）を追加し、親 PJ の実装と一致させる。子 PJ 側テストで両者の値が一致することを回帰テストとして固定する。

#### D-2: 親 PJ の `evaluate_kpis()` は v0.1 がデフォルトのままで、m-S1「deprecation warning」は未実装 — 新規戦略が v0.3 必須ゲートを無警告で回避できる

**問題**: 親 PJ Phase 2 マージのコミットメッセージは「Minor (m-S2, m-R2, m-R3, m-S1) merged: - m-S1: v0.1 deprecation warning」と明記しているが、実際に親 PJ の `src/minmax_fx_dt/decision/criteria.py` を検証すると `warnings.warn` や `DeprecationWarning` の呼び出しは**一つも存在しない**（`grep` で 0 件）。加えて `evaluate_kpis(stats, *, version: str = "v0.1")` は**デフォルトが v0.1 のまま**である。

したがって、`version` 引数を明示的に指定しない既存・新規のすべての呼び出しは、K4m=1.2・n_hard_floor=60・DSR 必須化のいずれも適用されない v0.1 の緩い基準で評価され続け、しかも呼び出し元には何の警告も出ない。これは v0.3 spec §10「オープン問題」や G タスク投入プロンプト自身が懸念していた「新規戦略が v0.3 必須ゲートを回避する抜け道」そのものであり、実際に**コード上ノーガードで存在する**ことを確認した。

（対照的に、子 PJ 側の `evaluate_kpis()` は `version="v0.1"` を渡すと `DeprecationWarning` を出す実装になっているが、デフォルトは `"v0.2"` であって `"v0.3"` に対応する分岐自体が無いため、そもそも v0.3 への誘導になっていない — D-1 参照。）

**影響**: 親 PJ で今後 SYS-FX026 以降の新規戦略を評価する際、担当者が `version="v0.3"` を明示的に指定し忘れると、v0.3 必須ゲートが全てスキップされたまま「評価済み」として記録されるリスクがある。

**修正案**:
1. 親 PJ `evaluate_kpis()` のデフォルトを `version="v0.1"` から `version="v0.3"` に変更する（後方互換が必要な既存呼び出し箇所のみ明示的に `version="v0.1"` を指定させる）か、
2. 最低限、`version` 未指定時に `DeprecationWarning`（もしくは v0.1 使用時のみ）を実際に発火させるコードを追加する。
3. コミットメッセージが実装内容と一致するよう、テスト（例: `pytest.warns(DeprecationWarning)` で v0.1 呼び出しをテスト）で保証する。

## 5. Mavis 環境 C 査読 (20-c-review.md) 17 findings の妥当性再評価

| ID | Mavis 判定 | あなたの再評価 | 理由 |
|---|---|---|---|
| M-S1 (K4m 1.2 緩和の文献出典) | Major | **不同意（未解決）** | spec 自身が「実物未確認・要出典検証」と明記したまま必須ゲート化されている。かつ章番号（第12章）とタイトルの組み合わせが疑わしい（本レポート C-2）。 |
| M-S2 (DSR_PASS_CAP 追加) | Major | **部分的に同意** | spec 記載としては追加されたが、コード上は完全に未実装（本レポート m-1）。「対応済み」と扱うのは時期尚早。 |
| M-S3 (n_hard_floor=50→安全弁根拠) | Major | **不同意（別の問題に置き換わっただけ）** | 60 への引き上げ自体はしたが、根拠とする「Bailey 2014 MinTRL T=60+」が誤帰属・誤引用（本レポート M-1）。加えて子PJには未反映（D-1）。 |
| M-D1 (compute_sharpe_z 抽出) | Major | **同意（適切に対応済み）** | 実装を確認した限り、PSR/DSR/z_statistic が単一の pure function で計算されるようになっており、意図通り機能している。 |
| M-R1 (DSR 分布 p5/p50/p95) | Major | **同意だが運用面で新たな懸念**（本レポート M-2） | 分布計算自体は正しく実装・実行されている（`dsr_distribution_v03.json`）。ただしその結果（0/4 通過）を受けた Task I の「緩和して救済」提案は HARKing リスクを孕む。 |
| M-R2 (n_trials 厳密カウント) | Major | **同意（方向性は正しいが数値の一貫性に要注意）** | 通貨・閾値選択を含める設計は妥当。ただし conservative(積) と liberal(和) の呼称と大小関係がケースによって直感に反する場合がある点は要ドキュメント化（軽微）。 |
| C-R1 (SYS-FX010 合成データ) | Critical | **同意（継続して適切に処理されている）** | portfolio-ledger.md で一貫して「⚠️合成」と明示され続けており、後続文書でも PASS サマリの母数から除外する扱いが維持されている。 |
| m-S1 (v0.1/v0.2 切替 API の誤用リスク) | Minor | **格上げを推奨（Major相当）** | 子 PJ では v0.1→v0.2 の deprecation warning が実装されたが、親 PJ では「実装した」とコミットメッセージに書かれているのに実際には存在しない（本レポート D-2）。これは Minor で済む問題ではなくなっている。 |
| m-S2 (NaN ハンドリング未定義) | Minor | **同意（適切に対応済み）** | `deflated_sharpe_ratio()` 冒頭で `np.isfinite` チェックと明確な `ValueError` が実装されている。 |
| m-S3 (DSR閾値の文献根拠がコメントのみ) | Minor | **格上げ（Critical相当）** | 対応として追加された引用が実際には論文に存在しない可能性が高いことが判明した（本レポート B-1）。「対応済み」ではなく新たな Critical 事案。 |
| m-S4 (permutation_test_clustered 非推奨が不徹底) | Minor | **同意（適切に強化）** | `PendingDeprecationWarning` への格上げ・v1.0 での削除方針の明記を確認。 |
| m-S5 (PJ000001 完了条件の曖昧さ) | Minor | 未検証 | 本査読のスコープ（対象A/B/C）外のため直接確認していない。次回査読での確認を推奨。 |
| m-D1 (N=1 特別扱いの docstring) | Minor | **同意（適切に対応済み）** | docstring に PSR との同値性の解釈が明記されている。 |
| m-D2 (fisher=True/False の混同リスク) | Minor | **同意（部分的に対応）** | docstring 明記に加え、`kurtosis < 1.5` での警告も追加されたが、境界値の設計は改善余地あり（本レポート B-2）。 |
| m-R1 (n_trials 二段階カウントが spec 未定義) | Minor | **同意（適切に対応済み）** | `00-spec-v0.3.md` §5 で conservative/liberal の定義が明文化されている。 |
| m-R2 (periods_per_year 未規定) | Minor | **同意（適切に対応済み）** | `valid_periods` チェックと警告が実装され、docstring にも正規化ルールが明記されている。 |
| m-R3 (結果 JSON の schema 未定義) | Minor | **同意（適切に対応済み）** | `DeflatedSharpeRatioResult.SCHEMA_VERSION` が導入され、`to_dict()` の破壊的変更禁止がコメントで明示されている。 |

## 6. 推奨アクション

**即修正（Critical）**:
1. `PHASE2_MERGE_PROPOSAL.md` の SYS-FX011 T-13 「PASS (p5=0.9961)」記載を訂正し、親 PJ マージコミット記録にも訂正ノートを追記する（C-1）。
2. `dsr.py` のコメントから実在しない "Table 1"・"Figure 2"・引用文を削除し、0.95 を「本 PJ 独自の設計判断」として正直に記載し直す（B-1）。
3. 文献引用全般（Lopez de Prado 2018 の章番号、Bailey 2014 の MinTRL）について、実物での検証を完了するまで spec 上に「⚠️未検証」フラグを維持する（C-2, M-1）。

**修正必要（Major、1-2週間以内）**:
4. 子 PJ `criteria.py` に `KPI_THRESHOLDS_V0_3` / v0.3 dispatch を追加し、親 PJ の実装と一致させる（D-1）。
5. 親 PJ `evaluate_kpis()` のデフォルト version を見直すか、v0.1 使用時に実際に警告を発火させる（D-2）。
6. `dsr_p5_sensitivity_report.md` の「案B」に HARKing リスクの警告を追記、または削除する（M-2）。
7. DSR_PASS_CAP=5/年 を最低限の自動集計スクリプトで補強する（m-1）。

**現状維持で良い部分**:
- `compute_sharpe_z()` による PSR/DSR/z_statistic の統一（M-D1）は適切に実装されている。
- NaN/inf ハンドリング、periods_per_year 検証、schema version 明示など、Minor 指摘への対応の大部分は堅実に実装されている。
- `permutation_test_block()` のデフォルト化・非推奨化の運用は妥当。

**Phase 3 マージ（親 PJ への完全統合）については、上記 Critical 3件の是正を確認してから進めるべき**。現状のまま完全統合すると、監査証跡の誤りと文献根拠の未検証という 2 つの問題が「正式な PJ 成果物」として固定化されてしまう。

## 7. 変更履歴

- 2026-08-31: claude code 環境での真の独立 C 査読初版
