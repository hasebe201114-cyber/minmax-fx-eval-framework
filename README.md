# minmax-fx-eval-framework

FX 戦略評価のための統計的フレームワーク。`minmax-fx-day-trading-lab`（FX バックテスト・戦略検証の親 PJ）から評価系（KPI 定義・検定・複数試行補正）を抜き出して独立 PJ 化。

## 目的

親 PJ で 11 戦略を試行して全滅した原因を構造解析したところ、**評価フレームワーク自体に以下の問題**が確認された（2026-08-29 時点）:

1. **K4m (ペイオフレシオ ≥ 1.5)** が市場構造的に達成不能
2. **min_n_trades = 300** が「週1厳選」戦略と物理的矛盾
3. **permutation_test_clustered** が 4 通貨構成で p 値下限 0.3158 に張り付く
4. **K3m (最大連続損失 ≤ 5)** が i.i.d. 帰無分布下でも 60〜72% で PASS
5. **選択バイアスの補正なし**（19-28 試行・213 コミット蓄積後の研究で必須）

本 PJ はこれらの問題に対する**新しい評価フレームワーク（v0.2）**を設計・実装・検証する。

## スコープ

- **In**: KPI 閾値の導出・検定手法選定（DSR・permutation・block bootstrap）・複数試行補正
- **Out**: 新規戦略の考案・バックテストエンジン本体・フォワードテスト実行

## 姉妹プロジェクト

- 親 PJ: [minmax-fx-day-trading-lab](https://github.com/hasebe201114-cyber/minmax-fx-day-trading-lab)
- 戦略パイロット PJ: [minmax-trading-pilot](https://github.com/hasebe201114-cyber/minmax-trading-pilot)
- 検証 web 公開: [minmax-fx-research-web](https://github.com/hasebe201114-cyber/minmax-fx-research-web)

## ディレクトリ

```
minmax-fx-eval-framework/
├── CLAUDE.md          # プロジェクト規約
├── AGENTS.md          # エージェント向け指示
├── README.md          # 本ファイル
├── obs/               # 設計議論のナレッジベース
├── research/          # 設計の正本・根拠・比較
│   ├── ACTIVE.md
│   ├── STRATEGY-BRIEF.md
│   ├── フレームワーク再設計/
│   │   ├── 00-spec.md          # 設計正本 (v0.2)
│   │   ├── 01-エビデンス/
│   │   ├── 02-比較/
│   │   └── 03-過去判定遡及/
│   └── 関連/
│       └── 旧フレームワーク参照.md
├── src/minmax_fx_eval/
│   ├── decision/criteria.py
│   ├── statistics/
│   │   ├── permutation.py
│   │   ├── dsr.py
│   │   └── power.py
│   └── backtest/metrics.py
├── tests/
└── scripts/
    └── compare_frameworks.py
```

## ステータス

- **2026-08-29**: 起票。v0.2 設計ドラフト完了・DSR 雛形実装着手。

## ライセンス

個人開発（minmax チーム）
