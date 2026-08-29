"""NTrialsBreakdown の回帰テスト (v0.3 M-R2 対応)."""

from __future__ import annotations

import pytest

from minmax_fx_eval.statistics.n_trials_counter import (
    KNOWN_STRATEGY_N_TRIALS,
    NTrialsBreakdown,
    count_n_trials,
)


class TestCountNTrials:
    """count_n_trials() のテスト."""

    def test_single_loop_returns_one(self):
        """単一試行なら n_trials=1."""
        n = count_n_trials(n_improvement_loops=1)
        assert n == 1

    def test_multiple_loops(self):
        """3 改善ループ → n_trials=3."""
        n = count_n_trials(n_improvement_loops=3)
        assert n == 3

    def test_multiplicative(self):
        """保守的カウントは全自由度の積."""
        n = count_n_trials(
            n_improvement_loops=7,
            n_grid_search_combinations=1,
            n_currency_choices=2,
            n_threshold_choices=2,
        )
        assert n == 7 * 1 * 2 * 2  # 28

    def test_bug_fixes_dont_count(self):
        """bug_fixes は n_trials に影響しない."""
        n_with_bug = count_n_trials(n_improvement_loops=3, n_bug_fixes=2)
        n_without_bug = count_n_trials(n_improvement_loops=3)
        assert n_with_bug == n_without_bug == 3


class TestNTrialsBreakdown:
    """NTrialsBreakdown のテスト."""

    def test_conservative_vs_liberal(self):
        """conservative ≥ liberal（積 ≥ 和）— 積は和より大きいのが一般的."""
        b = NTrialsBreakdown(
            n_improvement_loops=7,
            n_grid_search_combinations=1,
            n_currency_choices=2,
            n_period_choices=1,
            n_threshold_choices=2,
        )
        assert b.conservative == 28  # 7 * 1 * 2 * 1 * 2
        assert b.liberal == 13  # 7 + 1 + 2 + 1 + 2
        assert b.conservative > b.liberal  # 積は和より大きい

    def test_to_dict_keys(self):
        """to_dict() の必須フィールド."""
        b = NTrialsBreakdown(n_improvement_loops=3)
        d = b.to_dict()
        required = {
            "n_improvement_loops", "n_grid_search_combinations",
            "n_currency_choices", "n_period_choices", "n_threshold_choices",
            "n_bug_fixes_excluded", "n_trials_conservative", "n_trials_liberal",
            "notes",
        }
        assert required.issubset(d.keys())


class TestKnownStrategyNTrials:
    """KNOWN_STRATEGY_N_TRIALS プリセットのテスト."""

    def test_sysfx007_n_trials(self):
        """SYS-FX007: 6 ablations."""
        b = KNOWN_STRATEGY_N_TRIALS["SYS-FX007"]
        assert b.conservative == 6
        assert b.n_grid_search_combinations == 6

    def test_sysfx011_v7_n_trials(self):
        """SYS-FX011 v7: 7 loops × 2 currencies × 2 thresholds = 28."""
        b = KNOWN_STRATEGY_N_TRIALS["SYS-FX011 v7"]
        assert b.conservative == 7 * 2 * 2  # 28
        assert b.n_bug_fixes >= 1  # 週末クローズ・重複トレードバグ

    def test_sysfx008_bug_fixes_excluded(self):
        """SYS-FX008: bug fix は n_trials に含まない."""
        b = KNOWN_STRATEGY_N_TRIALS["SYS-FX008"]
        # 3 改善ループのみ。bug fix 1 件は conservative に含まない
        assert b.conservative == 3
        assert b.n_bug_fixes == 1
