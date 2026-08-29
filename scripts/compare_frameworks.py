"""フレームワーク比較スクリプト — v0.1 vs v0.2 シミュレーション.

使用方法:
    python scripts/compare_frameworks.py

目的:
    親 PJ の 11 戦略に対して v0.2 フレームワークを適用した場合の判定変化を
    机上シミュレーションする。判定結果は原則変えない方針だが、DSR 値の
    追加・K4m 閾値変化による差分を確認する。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from minmax_fx_eval.decision.criteria import (
    evaluate_kpis,
    kpi_pass_summary,
)
from minmax_fx_eval.statistics.dsr import deflated_sharpe_ratio


# 親 PJ の 11 戦略の机上パラメータ（OBS000008, ACTIVE.md, SYSTEMS.md より）
# 各戦略の代表値（n・Sharpe・perm_p・payoff・DSR 推定用）
STRATEGY_PARAMS: list[dict[str, Any]] = [
    {
        "sys_id": "SYS-FX007",
        "name": "レンジブレイク・プルバック",
        "n_trades": 125,
        "sharpe_monthly": 0.0,
        "profit_factor_monthly": 1.0,
        "expectancy_jpy": 0.0,
        "max_dd_monthly_pct": 30.0,
        "payoff_ratio": 0.9,
        "max_consecutive_losses": 8,
        "win_rate": 0.40,
        "permutation_p_value": 0.80,
        "n_trials": 19,
        "current_verdict": "REJECT",
    },
    {
        "sys_id": "SYS-FX008",
        "name": "トレンドフォロー・MAクロス",
        "n_trades": 163,
        "sharpe_monthly": 0.85,
        "profit_factor_monthly": 1.05,
        "expectancy_jpy": 119.5,
        "max_dd_monthly_pct": 18.0,
        "payoff_ratio": 1.05,
        "max_consecutive_losses": 6,
        "win_rate": 0.52,
        "permutation_p_value": 0.058,
        "n_trials": 3,
        "current_verdict": "REJECT",
    },
    {
        "sys_id": "SYS-FX009 v2",
        "name": "上位足トレンド+ダブルトップ/ボトム",
        "n_trades": 179,
        "sharpe_monthly": 0.7,
        "profit_factor_monthly": 1.0,
        "expectancy_jpy": 0.0,
        "max_dd_monthly_pct": 22.0,
        "payoff_ratio": 0.95,
        "max_consecutive_losses": 7,
        "win_rate": 0.48,
        "permutation_p_value": 0.001,
        "n_trials": 1,
        "current_verdict": "REJECT (確定的)",
    },
    {
        "sys_id": "SYS-FX010",
        "name": "スワップポイントキャリー",
        "n_trades": 60,
        "sharpe_monthly": 4.721,
        "profit_factor_monthly": 2.731,
        "expectancy_jpy": 300.0,
        "max_dd_monthly_pct": 0.74,
        "payoff_ratio": 1.638,
        "max_consecutive_losses": 4,
        "win_rate": 0.65,
        "permutation_p_value": 0.45,
        "n_trials": 5,
        "current_verdict": "REJECT (78-86%が価格変動由来)",
    },
    {
        "sys_id": "SYS-FX011 (T-13)",
        "name": "ボラティリティ・ブレイク (T-13 トレール専業)",
        "n_trades": 524,
        "sharpe_monthly": 2.94,
        "profit_factor_monthly": 1.65,
        "expectancy_jpy": 250.0,
        "max_dd_monthly_pct": 11.28,
        "payoff_ratio": 1.087,
        "max_consecutive_losses": 6,
        "win_rate": 0.638,
        "permutation_p_value": 0.035,
        "n_trials": 7,
        "current_verdict": "保留",
    },
    {
        "sys_id": "SYS-FX012",
        "name": "H1ブレイク+N_BREAKOUT (凍結設計)",
        "n_trades": 100,  # 想定
        "sharpe_monthly": 2.397,
        "profit_factor_monthly": 1.759,
        "expectancy_jpy": 200.0,
        "max_dd_monthly_pct": 8.69,
        "payoff_ratio": 1.078,
        "max_consecutive_losses": 5,
        "win_rate": 0.58,
        "permutation_p_value": 0.031,
        "n_trials": 1,
        "current_verdict": "フォワードテスト中",
    },
    {
        "sys_id": "SYS-FX013",
        "name": "非JPY通貨での再現性検証",
        "n_trades": 200,
        "sharpe_monthly": -0.3,
        "profit_factor_monthly": 0.85,
        "expectancy_jpy": -50.0,
        "max_dd_monthly_pct": 35.0,
        "payoff_ratio": 0.8,
        "max_consecutive_losses": 10,
        "win_rate": 0.42,
        "permutation_p_value": 0.65,
        "n_trials": 1,
        "current_verdict": "不採用",
    },
    {
        "sys_id": "SYS-FX016",
        "name": "JPY クロス追加通貨 (CHF/CAD)",
        "n_trades": 427,
        "sharpe_monthly": 2.094,
        "profit_factor_monthly": 1.564,
        "expectancy_jpy": 150.0,
        "max_dd_monthly_pct": 13.75,
        "payoff_ratio": 1.034,
        "max_consecutive_losses": 7,
        "win_rate": 0.55,
        "permutation_p_value": 0.0649,
        "n_trials": 1,
        "current_verdict": "司令塔判断待ち",
    },
    {
        "sys_id": "SYS-FX018",
        "name": "breakeven_trigger_r=2.0",
        "n_trades": 219,
        "sharpe_monthly": 2.5,
        "profit_factor_monthly": 1.7,
        "expectancy_jpy": 180.0,
        "max_dd_monthly_pct": 9.5,
        "payoff_ratio": 1.549,
        "max_consecutive_losses": 5,
        "win_rate": 0.56,
        "permutation_p_value": 0.044,
        "n_trials": 1,
        "current_verdict": "司令塔判断待ち",
    },
]


def simulate_strategy(p: dict) -> dict:
    """1 戦略に対して v0.1/v0.2 シミュレーション."""
    # DSR 推定用 returns を生成（n_trades に対応する月次リターンを模擬）
    np.random.seed(hash(p["sys_id"]) & 0x7FFFFFFF)
    # sharpe_monthly と整合する月次リターンを生成
    monthly_return_mean = p["sharpe_monthly"] * 0.01
    monthly_return_std = 0.01
    returns = np.random.normal(monthly_return_mean, monthly_return_std, 24).tolist()  # 24 ヶ月分

    stats_v02 = {
        "n_trades": p["n_trades"],
        "sharpe_monthly": p["sharpe_monthly"],
        "profit_factor_monthly": p["profit_factor_monthly"],
        "expectancy_jpy": p["expectancy_jpy"],
        "max_dd_monthly_pct": p["max_dd_monthly_pct"],
        "max_dd_yearly_pct": p["max_dd_monthly_pct"] * 1.5,
        "payoff_ratio": p["payoff_ratio"],
        "max_consecutive_losses": p["max_consecutive_losses"],
        "edge_per_trade_jpy": p["expectancy_jpy"],
        "spread_round_trip_jpy": 20.0,
        "win_rate": p["win_rate"],
        "permutation_p_value": p["permutation_p_value"],
        "returns": returns,
        "n_trials": p["n_trials"],
        "periods_per_year": 12,  # 月次
    }

    # DSR 計算
    dsr_result = deflated_sharpe_ratio(returns, n_trials=p["n_trials"], periods_per_year=12)

    # v0.2 評価
    evals_v02 = evaluate_kpis(stats_v02, version="v0.2")
    summary_v02 = kpi_pass_summary(evals_v02)

    # v0.1 評価（参考）
    stats_v01 = {k: v for k, v in stats_v02.items() if k not in {"returns", "n_trials", "periods_per_year"}}
    evals_v01 = evaluate_kpis(stats_v01, version="v0.1")
    summary_v01 = kpi_pass_summary(evals_v01)

    return {
        "sys_id": p["sys_id"],
        "name": p["name"],
        "n_trades": p["n_trades"],
        "current_verdict": p["current_verdict"],
        "v01_pass": summary_v01["pass"],
        "v01_fail": summary_v01["fail"],
        "v01_pass_metrics": [e.metric for e in evals_v01 if e.pass_],
        "v01_fail_metrics": summary_v01["fail_metrics"],
        "v02_pass": summary_v02["pass"],
        "v02_fail": summary_v02["fail"],
        "v02_pass_metrics": [e.metric for e in evals_v02 if e.pass_],
        "v02_fail_metrics": summary_v02["fail_metrics"],
        "dsr": round(dsr_result.dsr, 4),
        "dsr_passes": dsr_result.passes_threshold,
        "sharpe_observed": round(dsr_result.sharpe_observed, 3),
        "e_max_sharpe": round(dsr_result.expected_max_sharpe, 3),
        "n_trials": p["n_trials"],
    }


def main() -> int:
    """メイン処理."""
    print("=" * 80)
    print("minmax-fx-eval-framework: Framework Comparison Simulation v0.1 vs v0.2")
    print("=" * 80)
    print()

    results = []
    for p in STRATEGY_PARAMS:
        result = simulate_strategy(p)
        results.append(result)

    # 結果表示
    for r in results:
        print(f"## {r['sys_id']}: {r['name']}")
        print(f"  現行判定: {r['current_verdict']}")
        print(f"  n_trades: {r['n_trades']}, n_trials(N): {r['n_trials']}")
        print(f"  v0.1: {r['v01_pass']} pass / {r['v01_fail']} fail")
        print(f"    pass: {r['v01_pass_metrics']}")
        print(f"    fail: {r['v01_fail_metrics']}")
        print(f"  v0.2: {r['v02_pass']} pass / {r['v02_fail']} fail")
        print(f"    pass: {r['v02_pass_metrics']}")
        print(f"    fail: {r['v02_fail_metrics']}")
        print(f"  DSR: {r['dsr']:.4f} {'(>=0.95 PASS)' if r['dsr_passes'] else '(<0.95 FAIL)'}")
        print(f"    SR_obs={r['sharpe_observed']}, E[max SR*]={r['e_max_sharpe']} (N={r['n_trials']})")
        print()

    # 結果保存
    output_dir = Path("research/フレームワーク再設計/02-比較")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "v01_vs_v02_simulation.json"
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"結果保存: {output_path}")
    print()

    # 集計
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    dsr_pass = sum(1 for r in results if r["dsr_passes"])
    print(f"DSR >= 0.95 PASS: {dsr_pass}/{len(results)} strategies")
    v01_pass = sum(1 for r in results if r["v01_fail"] == 0)
    v02_pass = sum(1 for r in results if r["v02_fail"] == 0)
    print(f"v0.1 all-pass: {v01_pass}/{len(results)} strategies")
    print(f"v0.2 all-pass: {v02_pass}/{len(results)} strategies")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
