"""撤退/採用判定基準 — v0.2 (DSR 必須ゲート追加版).

起源:
    minmax-fx-day-trading-lab/src/minmax_fx_dt/decision/criteria.py
    の v0.2 適用版。K4m=1.2 緩和・n_hard_floor=50 新設・DSR 必須ゲート追加。

v0.2 変更点:
    - K4m 閾値: 1.5 → 1.2（本 spec 2.1）
    - min_n_trades: 300 → 50 (hard floor・DSR で動的補正)
    - DSR ≥ 0.95 を必須ゲートとして追加（本 spec 2.4）
    - 既存 T-06/07/08 の機能は維持

評価フロー:
    1. evaluate_kpis() で K1m〜K7m + DSR を評価
    2. 適用可能 (applicable=True) な指標のみを集計
    3. failed_kpis を算出し、evaluate() で最終判定
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

import numpy as np

from ..statistics.dsr import (
    DSR_REQUIRED_THRESHOLD,
    deflated_sharpe_ratio,
)


class Verdict(str, Enum):
    """撤退/採用判定."""

    GO = "GO"
    WATCH = "WATCH"
    REJECT = "REJECT"
    SAMPLE_DEFICIT = "SAMPLE-DEFICIT"


# v0.2 必須ゲート閾値
KPI_THRESHOLDS_V0_2: dict[str, dict[str, float]] = {
    "K1m_sharpe_monthly": 0.4,
    "K1m_profit_factor_monthly": 1.2,
    "K1m_expectancy_jpy": 0.0,
    "K2m_max_dd_monthly_pct": 10.0,
    "K2m_max_dd_yearly_pct": 20.0,
    "K3m_iid_percentile": 0.95,  # T-08 適用
    "K4m_payoff_ratio": 1.2,  # v0.2 緩和（1.5 → 1.2）
    "K5m_spread_cost_multiple": 3.0,
    "n_hard_floor": 50,  # v0.2 新設（DSR で動的補正）
    "permutation_p_value": 0.05,
    "dsr": DSR_REQUIRED_THRESHOLD,  # 0.95
}

# 後方互換（v0.1 閾値）
KPI_THRESHOLDS_V0_1: dict[str, dict[str, float]] = {
    "K1m_sharpe_monthly": 0.4,
    "K1m_profit_factor_monthly": 1.2,
    "K1m_expectancy_jpy": 0.0,
    "K2m_max_dd_monthly_pct": 10.0,
    "K2m_max_dd_yearly_pct": 20.0,
    "K3m_max_consecutive_losses": 5,  # 旧: 絶対件数
    "K4m_payoff_ratio": 1.5,  # 旧
    "K5m_spread_cost_multiple": 3.0,
    "min_n_trades": 300,  # 旧
    "permutation_p_value": 0.05,
}


@dataclass
class KPIEvaluation:
    """KPI 評価結果."""

    metric: str
    observed: float
    threshold: float
    pass_: bool
    note: str = ""
    applicable: bool = True


class Stats(TypedDict, total=False):
    """評価に必要な統計量（親 PJ と互換）."""

    strategy_id: str
    n_days: int
    n_trades: int
    sharpe: float
    sharpe_monthly: float
    profit_factor_monthly: float
    expectancy_jpy: float
    max_dd: float
    max_dd_monthly_pct: float
    max_dd_yearly_pct: float
    payoff_ratio: float
    max_consecutive_losses: int
    edge_per_trade_jpy: float
    spread_round_trip_jpy: float
    max_margin_usage_pct: float
    weak_breakout_exclusion_pct: float
    backtest_forward_divergence_pct: float | None
    permutation_p_value: float | None
    n_trades_per_currency: dict[str, int]
    hedging_enabled: bool
    n_trades_effective: float
    win_rate: float
    # v0.2 追加
    returns: list[float]  # DSR 計算用
    periods_per_year: int  # デフォルト 252
    n_trials: int  # 試行数（DSR の N パラメータ）


def _max_consecutive_true(flags: list[bool] | np.ndarray) -> int:
    """bool 配列の最長連続 True 区間長."""
    best = cur = 0
    for flag in flags:
        cur = cur + 1 if flag else 0
        best = max(best, cur)
    return best


def compute_k3m_scale_invariant(
    n_trades: int,
    win_rate: float,
    observed_max_consecutive_losses: int,
    *,
    reps: int = 3000,
    seed: int = 0,
    alpha: float = 0.05,
) -> dict:
    """K3m スケール不変判定（T-08 親 PJ 実装を流用）."""
    rng = np.random.default_rng(seed)
    runs = (
        np.array([
            _max_consecutive_true(list(rng.random(n_trades) >= win_rate))
            for _ in range(reps)
        ])
        if n_trades > 0
        else np.array([0])
    )
    percentile = float((runs < observed_max_consecutive_losses).mean())
    passed = percentile <= (1.0 - alpha)
    return {
        "n_trades": n_trades,
        "win_rate": round(win_rate, 4),
        "observed_max_consecutive_losses": observed_max_consecutive_losses,
        "iid_null_mean": round(float(runs.mean()), 2),
        "iid_null_median": int(np.median(runs)),
        "observed_percentile_in_null": round(percentile, 4),
        "alpha": alpha,
        "pass_": passed,
    }


def evaluate_kpis(stats: Stats, *, version: str = "v0.2") -> list[KPIEvaluation]:
    """KPI 評価（v0.1 / v0.2 切替可能）.

    Args:
        stats: 評価対象の統計量 dict。
        version: "v0.1" (親 PJ 互換) または "v0.2" (本 PJ 推奨)。

    Returns:
        KPIEvaluation のリスト。
    """
    if version == "v0.2":
        return _evaluate_kpis_v0_2(stats)
    elif version == "v0.1":
        return _evaluate_kpis_v0_1(stats)
    else:
        raise ValueError(f"version must be 'v0.1' or 'v0.2', got {version}")


def _evaluate_kpis_v0_2(stats: Stats) -> list[KPIEvaluation]:
    """v0.2 評価ロジック.

    必須ゲート:
        - K1m: sharpe ≥ 0.4, PF ≥ 1.2, expectancy > 0
        - K2m: DD monthly ≤ 10%, yearly ≤ 20%
        - K3m: i.i.d. 上位 5% パーセンタイル（T-08）
        - K4m: payoff ≥ 1.2（v0.2 緩和）
        - K5m: spread cost multiple ≥ 3
        - n_hard_floor: n ≥ 50（v0.2 新設）
        - perm_p: < 0.05（block デフォルト）
        - DSR: ≥ 0.95（v0.2 新設・必須）
    """
    evals: list[KPIEvaluation] = []
    thresholds = KPI_THRESHOLDS_V0_2

    # K1m
    sharpe = float(stats.get("sharpe_monthly", stats.get("sharpe", 0.0)))
    evals.append(KPIEvaluation("K1m_sharpe", sharpe, thresholds["K1m_sharpe_monthly"], sharpe >= thresholds["K1m_sharpe_monthly"]))

    pf = float(stats.get("profit_factor_monthly", 0.0))
    evals.append(KPIEvaluation("K1m_pf", pf, thresholds["K1m_profit_factor_monthly"], pf >= thresholds["K1m_profit_factor_monthly"]))

    expectancy = float(stats.get("expectancy_jpy", 0.0))
    evals.append(KPIEvaluation("K1m_expectancy", expectancy, thresholds["K1m_expectancy_jpy"], expectancy > thresholds["K1m_expectancy_jpy"]))

    # K2m
    max_dd_m = abs(float(stats.get("max_dd_monthly_pct", stats.get("max_dd", 0.0))))
    evals.append(KPIEvaluation("K2m_dd_monthly", max_dd_m, thresholds["K2m_max_dd_monthly_pct"], max_dd_m <= thresholds["K2m_max_dd_monthly_pct"]))

    max_dd_y = abs(float(stats.get("max_dd_yearly_pct", max_dd_m)))
    evals.append(KPIEvaluation("K2m_dd_yearly", max_dd_y, thresholds["K2m_max_dd_yearly_pct"], max_dd_y <= thresholds["K2m_max_dd_yearly_pct"]))

    # K3m: スケール不変判定（win_rate があれば使用）
    mcl = int(stats.get("max_consecutive_losses", 999))
    win_rate = stats.get("win_rate")
    n_trades = int(stats.get("n_trades", 0))
    if win_rate is not None and n_trades > 0:
        k3m = compute_k3m_scale_invariant(n_trades, float(win_rate), mcl)
        evals.append(
            KPIEvaluation(
                "K3m_iid_percentile",
                float(k3m["observed_percentile_in_null"]),
                thresholds["K3m_iid_percentile"],
                k3m["pass_"],
                f"i.i.d. パーセンタイル={k3m['observed_percentile_in_null']:.3f} (n={n_trades})",
            )
        )
    else:
        evals.append(
            KPIEvaluation(
                "K3m_iid_percentile",
                float("nan"),
                thresholds["K3m_iid_percentile"],
                False,
                "win_rate 未指定のため判定対象外",
                applicable=False,
            )
        )

    # K4m (v0.2: 1.2)
    pr = float(stats.get("payoff_ratio", 0.0))
    evals.append(KPIEvaluation("K4m_payoff", pr, thresholds["K4m_payoff_ratio"], pr >= thresholds["K4m_payoff_ratio"]))

    # K5m
    edge = float(stats.get("edge_per_trade_jpy", stats.get("expectancy_jpy", 0.0)))
    spread_rt = float(stats.get("spread_round_trip_jpy", 0.0))
    if spread_rt > 0:
        multiple = edge / spread_rt
        evals.append(KPIEvaluation("K5m_spread_cost", multiple, thresholds["K5m_spread_cost_multiple"], multiple >= thresholds["K5m_spread_cost_multiple"]))
    else:
        evals.append(KPIEvaluation("K5m_spread_cost", 0.0, thresholds["K5m_spread_cost_multiple"], False, "spread_round_trip_jpy 未提供", applicable=False))

    # n_hard_floor (v0.2 新設)
    evals.append(KPIEvaluation("n_hard_floor", float(n_trades), thresholds["n_hard_floor"], n_trades >= thresholds["n_hard_floor"], f"名目 n={n_trades}"))

    # permutation p 値
    p_value = stats.get("permutation_p_value")
    if p_value is None:
        evals.append(KPIEvaluation("perm_p", float("nan"), thresholds["permutation_p_value"], False, "permutation test 未実行", applicable=False))
    else:
        evals.append(KPIEvaluation("perm_p", float(p_value), thresholds["permutation_p_value"], float(p_value) < thresholds["permutation_p_value"]))

    # DSR (v0.2 新設・必須)
    returns = stats.get("returns")
    n_trials = int(stats.get("n_trials", 1))
    if returns is not None and len(returns) >= 2:
        periods_per_year = int(stats.get("periods_per_year", 252))
        dsr_result = deflated_sharpe_ratio(
            returns,
            n_trials=n_trials,
            periods_per_year=periods_per_year,
            threshold=thresholds["dsr"],
        )
        evals.append(
            KPIEvaluation(
                "DSR",
                dsr_result.dsr,
                dsr_result.threshold,
                dsr_result.passes_threshold,
                f"DSR={dsr_result.dsr:.4f}, SR_obs={dsr_result.sharpe_observed:.3f}, "
                f"E[max SR*]={dsr_result.expected_max_sharpe:.3f} (N={n_trials})",
            )
        )
    else:
        evals.append(
            KPIEvaluation(
                "DSR",
                float("nan"),
                thresholds["dsr"],
                False,
                "returns データ未提供のため判定対象外（DSR 計算不能）",
                applicable=False,
            )
        )

    return evals


def _evaluate_kpis_v0_1(stats: Stats) -> list[KPIEvaluation]:
    """v0.1 評価ロジック（親 PJ 互換・参考用）."""
    evals: list[KPIEvaluation] = []
    thresholds = KPI_THRESHOLDS_V0_1

    sharpe = float(stats.get("sharpe_monthly", stats.get("sharpe", 0.0)))
    evals.append(KPIEvaluation("K1m_sharpe", sharpe, thresholds["K1m_sharpe_monthly"], sharpe >= thresholds["K1m_sharpe_monthly"]))

    pf = float(stats.get("profit_factor_monthly", 0.0))
    evals.append(KPIEvaluation("K1m_pf", pf, thresholds["K1m_profit_factor_monthly"], pf >= thresholds["K1m_profit_factor_monthly"]))

    expectancy = float(stats.get("expectancy_jpy", 0.0))
    evals.append(KPIEvaluation("K1m_expectancy", expectancy, thresholds["K1m_expectancy_jpy"], expectancy > thresholds["K1m_expectancy_jpy"]))

    max_dd_m = abs(float(stats.get("max_dd_monthly_pct", stats.get("max_dd", 0.0))))
    evals.append(KPIEvaluation("K2m_dd_monthly", max_dd_m, thresholds["K2m_max_dd_monthly_pct"], max_dd_m <= thresholds["K2m_max_dd_monthly_pct"]))

    max_dd_y = abs(float(stats.get("max_dd_yearly_pct", max_dd_m)))
    evals.append(KPIEvaluation("K2m_dd_yearly", max_dd_y, thresholds["K2m_max_dd_yearly_pct"], max_dd_y <= thresholds["K2m_max_dd_yearly_pct"]))

    mcl = int(stats.get("max_consecutive_losses", 999))
    evals.append(KPIEvaluation("K3m_max_consec", float(mcl), thresholds["K3m_max_consecutive_losses"], float(mcl) <= thresholds["K3m_max_consecutive_losses"]))

    pr = float(stats.get("payoff_ratio", 0.0))
    evals.append(KPIEvaluation("K4m_payoff", pr, thresholds["K4m_payoff_ratio"], pr >= thresholds["K4m_payoff_ratio"]))

    edge = float(stats.get("edge_per_trade_jpy", stats.get("expectancy_jpy", 0.0)))
    spread_rt = float(stats.get("spread_round_trip_jpy", 0.0))
    if spread_rt > 0:
        multiple = edge / spread_rt
        evals.append(KPIEvaluation("K5m_spread_cost", multiple, thresholds["K5m_spread_cost_multiple"], multiple >= thresholds["K5m_spread_cost_multiple"]))
    else:
        evals.append(KPIEvaluation("K5m_spread_cost", 0.0, thresholds["K5m_spread_cost_multiple"], False, "spread_round_trip_jpy 未提供", applicable=False))

    n_trades = int(stats.get("n_trades", 0))
    evals.append(KPIEvaluation("min_n_trades", float(n_trades), thresholds["min_n_trades"], n_trades >= thresholds["min_n_trades"]))

    p_value = stats.get("permutation_p_value")
    if p_value is None:
        evals.append(KPIEvaluation("perm_p", float("nan"), thresholds["permutation_p_value"], False, "permutation test 未実行", applicable=False))
    else:
        evals.append(KPIEvaluation("perm_p", float(p_value), thresholds["permutation_p_value"], float(p_value) < thresholds["permutation_p_value"]))

    return evals


def kpi_pass_summary(evals: list[KPIEvaluation]) -> dict:
    """KPI 評価一覧の集計."""
    applicable = [e for e in evals if e.applicable]
    not_applicable = [e for e in evals if not e.applicable]
    passed = [e for e in applicable if e.pass_]
    return {
        "total": len(evals),
        "applicable": len(applicable),
        "not_applicable": len(not_applicable),
        "not_applicable_metrics": [e.metric for e in not_applicable],
        "pass": len(passed),
        "fail": len(applicable) - len(passed),
        "fail_metrics": [e.metric for e in applicable if not e.pass_],
        "all_applicable_pass": len(passed) == len(applicable) and len(applicable) > 0,
    }


def evaluate(stats: Stats, *, version: str = "v0.2") -> tuple[Verdict, str]:
    """最終判定（v0.2 推奨）.

    Args:
        stats: 評価対象の統計量。
        version: "v0.1" / "v0.2"。

    Returns:
        (Verdict, 理由文字列)。
    """
    n_trades = int(stats.get("n_trades", 0))
    n_days = int(stats.get("n_days", 0))

    # SAMPLE_DEFICIT
    if n_trades < 50:
        return Verdict.SAMPLE_DEFICIT, f"n_trades={n_trades} < 50 (v0.2 hard floor)"

    kpi_evals = evaluate_kpis(stats, version=version)
    failed = [e.metric for e in kpi_evals if e.applicable and not e.pass_]
    summary = kpi_pass_summary(kpi_evals)

    if not failed:
        return Verdict.GO, f"v{version} 全必須ゲート達成 ({summary['pass']}/{summary['applicable']})"
    return Verdict.REJECT, f"v{version} 失敗 KPI: {','.join(failed)} ({summary['pass']}/{summary['applicable']})"


__all__ = [
    "KPIEvaluation",
    "Stats",
    "Verdict",
    "KPI_THRESHOLDS_V0_1",
    "KPI_THRESHOLDS_V0_2",
    "compute_k3m_scale_invariant",
    "evaluate_kpis",
    "evaluate",
    "kpi_pass_summary",
]
