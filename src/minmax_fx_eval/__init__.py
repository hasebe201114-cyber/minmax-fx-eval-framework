"""minmax-fx-eval: FX 戦略評価フレームワーク.

起源:
    minmax-fx-day-trading-lab の評価系コード（decision/criteria.py,
    backtest/permutation.py）を分離・独立 PJ 化した姉妹 PJ。

スコープ:
    - KPI 評価（K1m〜K7m + 統計的有意性ゲート）
    - 統計検定（permutation test, Deflated Sharpe Ratio）
    - 検出力計算（min_n_trades の動的導出）
    - 複数試行補正

非スコープ:
    - 新規取引戦略の考案
    - バックテストエンジン本体
    - フォワードテストの実行
"""

__version__ = "0.1.0"
