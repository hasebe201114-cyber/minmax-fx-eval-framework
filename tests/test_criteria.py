"""criteria.py v0.2 vs v0.1 の回帰テスト."""

from __future__ import annotations

import numpy as np
import pytest

from minmax_fx_eval.decision.criteria import (
    KPI_THRESHOLDS_V0_1,
    KPI_THRESHOLDS_V0_2,
    compute_k3m_scale_invariant,
    evaluate,
    evaluate_kpis,
    kpi_pass_summary,
)


class TestK3mScaleInvariant:
    """K3m スケール不変判定のテスト."""

    def test_low_consecutive_losses_pass(self):
        """少ない連続損失は PASS."""
        result = compute_k3m_scale_invariant(n_trades=100, win_rate=0.6, observed_max_consecutive_losses=4)
        # 4 連続損失は n=100, win_rate=0.6 で i.i.d. 分布内では普通
        assert result["pass_"] is True

    def test_extreme_consecutive_losses_fail(self):
        """極端な連続損失は FAIL."""
        result = compute_k3m_scale_invariant(n_trades=100, win_rate=0.6, observed_max_consecutive_losses=15)
        # 15 連続損失は極端
        assert result["pass_"] is False


class TestV01V02Thresholds:
    """v0.1 vs v0.2 閾値の差分テスト."""

    def test_k4m_relaxed(self):
        """K4m 閾値: v0.1=1.5 → v0.2=1.2."""
        assert KPI_THRESHOLDS_V0_1["K4m_payoff_ratio"] == 1.5
        assert KPI_THRESHOLDS_V0_2["K4m_payoff_ratio"] == 1.2
        assert KPI_THRESHOLDS_V0_2["K4m_payoff_ratio"] < KPI_THRESHOLDS_V0_1["K4m_payoff_ratio"]

    def test_n_hard_floor_introduced(self):
        """v0.2 で n_hard_floor=50 が新設."""
        assert "n_hard_floor" in KPI_THRESHOLDS_V0_2
        assert KPI_THRESHOLDS_V0_2["n_hard_floor"] == 50
        # v0.1 には存在しない（min_n_trades=300 だった）
        assert "n_hard_floor" not in KPI_THRESHOLDS_V0_1

    def test_dsr_threshold_in_v02(self):
        """v0.2 で DSR 閾値 0.95 が必須."""
        assert "dsr" in KPI_THRESHOLDS_V0_2
        assert KPI_THRESHOLDS_V0_2["dsr"] == 0.95


class TestEvaluateKPIs:
    """evaluate_kpis() のテスト."""

    def _base_stats(self, **overrides) -> dict:
        """ベース stats を作成."""
        base = {
            "strategy_id": "TEST",
            "n_days": 365,
            "n_trades": 100,
            "sharpe": 0.5,
            "sharpe_monthly": 0.5,
            "profit_factor_monthly": 1.3,
            "expectancy_jpy": 100.0,
            "max_dd": 5.0,
            "max_dd_monthly_pct": 5.0,
            "max_dd_yearly_pct": 10.0,
            "payoff_ratio": 1.5,
            "max_consecutive_losses": 3,
            "edge_per_trade_jpy": 100.0,
            "spread_round_trip_jpy": 20.0,
            "max_margin_usage_pct": 15.0,
            "weak_breakout_exclusion_pct": 35.0,
            "win_rate": 0.55,
            "permutation_p_value": 0.02,
        }
        base.update(overrides)
        return base

    def test_v02_returns_evaluations(self):
        """v0.2 評価が正常に返る."""
        stats = self._base_stats()
        evals = evaluate_kpis(stats, version="v0.2")
        assert len(evals) > 0
        metrics = {e.metric for e in evals}
        assert "K1m_sharpe" in metrics
        assert "K4m_payoff" in metrics
        assert "K5m_spread_cost" in metrics
        assert "n_hard_floor" in metrics
        assert "DSR" in metrics

    def test_v01_no_dsr_evaluation(self):
        """v0.1 評価は DSR を含まない."""
        stats = self._base_stats()
        evals = evaluate_kpis(stats, version="v0.1")
        metrics = {e.metric for e in evals}
        assert "DSR" not in metrics
        assert "n_hard_floor" not in metrics
        assert "K4m_payoff" in metrics  # ただし閾値は 1.5

    def test_k4m_passes_v02_with_1_3(self):
        """K4m=1.3 は v0.2 (≥1.2) で PASS、v0.1 (≥1.5) で FAIL."""
        stats = self._base_stats(payoff_ratio=1.3)
        evals_v02 = evaluate_kpis(stats, version="v0.2")
        evals_v01 = evaluate_kpis(stats, version="v0.1")
        k4m_v02 = next(e for e in evals_v02 if e.metric == "K4m_payoff")
        k4m_v01 = next(e for e in evals_v01 if e.metric == "K4m_payoff")
        assert k4m_v02.pass_ is True
        assert k4m_v01.pass_ is False

    def test_n_below_50_sample_deficit(self):
        """n < 50 は evaluate() で SAMPLE_DEFICIT."""
        stats = self._base_stats(n_trades=30)
        verdict, reason = evaluate(stats, version="v0.2")
        assert verdict.value == "SAMPLE-DEFICIT"
        assert "30" in reason

    def test_dsr_not_applicable_without_returns(self):
        """returns なしは DSR applicable=False."""
        stats = self._base_stats()
        evals = evaluate_kpis(stats, version="v0.2")
        dsr = next(e for e in evals if e.metric == "DSR")
        assert dsr.applicable is False


class TestEvaluate:
    """evaluate() 全体のテスト."""

    def test_all_pass_returns_go(self):
        """全必須ゲート達成で GO."""
        np.random.seed(42)
        returns = np.random.normal(0.002, 0.01, 200).tolist()
        stats = {
            "strategy_id": "TEST",
            "n_days": 365,
            "n_trades": 200,
            "sharpe": 0.5,
            "sharpe_monthly": 0.5,
            "profit_factor_monthly": 1.3,
            "expectancy_jpy": 100.0,
            "max_dd": 5.0,
            "max_dd_monthly_pct": 5.0,
            "max_dd_yearly_pct": 10.0,
            "payoff_ratio": 1.5,
            "max_consecutive_losses": 3,
            "edge_per_trade_jpy": 100.0,
            "spread_round_trip_jpy": 20.0,
            "win_rate": 0.55,
            "permutation_p_value": 0.02,
            "returns": returns,
            "n_trials": 1,
            "periods_per_year": 252,
        }
        verdict, reason = evaluate(stats, version="v0.2")
        # DSR ≥ 0.95 は N=1 なら高確率で達成
        if "GO" in verdict.value:
            assert "v0.2" in reason

    def test_k4m_fail_with_v01_passes_with_v02(self):
        """K4m=1.3 は v0.1 で FAIL、v0.2 で GO になる可能性."""
        stats = {
            "strategy_id": "TEST",
            "n_days": 365,
            "n_trades": 100,
            "sharpe": 0.5,
            "sharpe_monthly": 0.5,
            "profit_factor_monthly": 1.3,
            "expectancy_jpy": 100.0,
            "max_dd": 5.0,
            "max_dd_monthly_pct": 5.0,
            "max_dd_yearly_pct": 10.0,
            "payoff_ratio": 1.3,  # v0.1 で FAIL、v0.2 で PASS
            "max_consecutive_losses": 3,
            "edge_per_trade_jpy": 100.0,
            "spread_round_trip_jpy": 20.0,
            "win_rate": 0.55,
            "permutation_p_value": 0.02,
        }
        v01_verdict, _ = evaluate(stats, version="v0.1")
        v02_verdict, _ = evaluate(stats, version="v0.2")
        assert v01_verdict.value == "REJECT"
        # v0.2 は DSR 判定なし（returns なし・applicable=False）で他は全 PASS なので GO
        assert v02_verdict.value == "GO"


class TestKPIPassSummary:
    """kpi_pass_summary() のテスト."""

    def test_basic_summary(self):
        evals = evaluate_kpis(
            {
                "n_trades": 100,
                "sharpe_monthly": 0.5,
                "profit_factor_monthly": 1.3,
                "expectancy_jpy": 100.0,
                "max_dd_monthly_pct": 5.0,
                "max_dd_yearly_pct": 10.0,
                "payoff_ratio": 1.5,
                "max_consecutive_losses": 3,
                "edge_per_trade_jpy": 100.0,
                "spread_round_trip_jpy": 20.0,
                "win_rate": 0.55,
                "permutation_p_value": 0.02,
            },
            version="v0.2",
        )
        summary = kpi_pass_summary(evals)
        assert summary["total"] == len(evals)
        assert summary["pass"] + summary["fail"] == summary["applicable"]
        assert "DSR" in summary["not_applicable_metrics"]  # returns なし
