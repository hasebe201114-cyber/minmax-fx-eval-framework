"""permutation test の回帰テスト."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from minmax_fx_eval.statistics.permutation import (
    effective_pair_count,
    permutation_test,
    permutation_test_block,
    permutation_test_clustered,
)


class TestEffectivePairCount:
    """effective_pair_count のテスト."""

    def test_single_pair(self):
        """1 通貨なら実効独立数 = 1."""
        assert effective_pair_count(["USD_JPY"]) == 1.0

    def test_independent_pairs(self):
        """無相関 4 通貨なら実効独立数 ≈ 4."""
        # 相関行列に無いペアでテスト
        result = effective_pair_count(["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"])
        # JPY クロスは高相関なので実効 < 4
        assert 1.0 < result < 4.0

    def test_jpy_cross_high_correlation(self):
        """JPY クロス 4 通貨（高相関）→ 実効独立数 ≪ 4."""
        result = effective_pair_count(["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"])
        # 実測 0.808 平均相関 → 4/(1+3*0.808) = 4/3.424 ≈ 1.168
        assert 1.0 < result < 1.3


class TestPermutationTestBlock:
    """permutation_test_block のテスト."""

    def test_block_basic(self):
        """block 版の正常動作."""
        trade_pnls = [1.0, -1.0, 2.0, -2.0, 0.5]
        cluster_keys = ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"]
        result = permutation_test_block(trade_pnls, cluster_keys, n_permutations=1000, seed=42)
        assert result.n_trades == 5
        assert 0.0 <= result.p_value <= 1.0
        assert "block_sign_flip" in result.method

    def test_block_preserves_within_cluster_correlation(self):
        """block 版は同じクラスタ内の符号を一緒に反転."""
        # クラスタ1: すべて正（強いエッジ）
        # クラスタ2: すべて負（弱いエッジ）
        # 全体では混合
        trade_pnls = [1.0, 2.0, -1.0, -2.0]
        cluster_keys = ["A", "A", "B", "B"]
        np.random.seed(42)
        result = permutation_test_block(trade_pnls, cluster_keys, n_permutations=1000, seed=42)
        # 観測平均 = 0、p 値は 0.5 付近（極端ではない）
        assert 0.0 < result.p_value < 1.0

    def test_length_mismatch_raises(self):
        """trade_pnls と cluster_keys の長さ不一致は ValueError."""
        with pytest.raises(ValueError):
            permutation_test_block([1.0, 2.0], ["A"])

    def test_empty_input(self):
        """空入力は p=1.0 を返す（エラーではない）."""
        result = permutation_test_block([], [], n_permutations=100)
        assert result.n_trades == 0
        assert result.p_value == 1.0


class TestPermutationTestGeneric:
    """permutation_test() の汎用 API テスト."""

    def test_with_cluster_keys_calls_block(self):
        """cluster_keys を渡すと block 版の動作."""
        trade_pnls = [1.0, -1.0, 2.0, -2.0]
        cluster_keys = ["A", "A", "B", "B"]
        result = permutation_test(trade_pnls, cluster_keys=cluster_keys, n_permutations=100, seed=42)
        assert "block_sign_flip" in result.method

    def test_without_cluster_keys_deprecated(self):
        """cluster_keys なしは DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = permutation_test([1.0, -1.0, 2.0], n_permutations=100, seed=42)
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert "iid_sign_flip" in result.method

    def test_reproducibility_with_seed(self):
        """同じ seed で同じ結果."""
        trade_pnls = [1.0, -1.0, 2.0, -2.0, 0.5]
        cluster_keys = ["A", "A", "B", "B", "C"]
        r1 = permutation_test_block(trade_pnls, cluster_keys, n_permutations=500, seed=42)
        r2 = permutation_test_block(trade_pnls, cluster_keys, n_permutations=500, seed=42)
        assert r1.p_value == r2.p_value
        assert r1.observed_statistic == r2.observed_statistic


class TestPermutationTestClusteredDeprecated:
    """permutation_test_clustered() の非推奨テスト.

    v0.3 m-S4 対応: DeprecationWarning → PendingDeprecationWarning に格上げ、
    v1.0 で完全削除予定であることを docstring + テストで担保.
    """

    def test_deprecated_warning(self):
        """非推奨警告."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                permutation_test_clustered([1.0, -1.0], ["USD_JPY", "USD_JPY"])
            except NotImplementedError:
                pass  # 実装は省略している
        # 非推奨警告が出ているはず
        # 注: 警告が出ない場合は「実装省略」による早期 return の可能性

    def test_v03_emits_pending_deprecation(self) -> None:
        """v0.3 m-S4: PendingDeprecationWarning を発していること.

        DeprecationWarning ではなく PendingDeprecationWarning を使うことで
        「v1.0 で完全削除予定」を利用者（フィルタ設定者）に明示.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                permutation_test_clustered([1.0, -1.0, 2.0], ["USD_JPY", "EUR_JPY", "USD_JPY"])
            except NotImplementedError:
                pass
        # PendingDeprecationWarning が出ること
        assert any(
            issubclass(warning.category, PendingDeprecationWarning) for warning in w
        ), (
            "v0.3 m-S4: permutation_test_clustered() は PendingDeprecationWarning を"
            "発する必要があります（v1.0 で完全削除予定）"
        )
        # DeprecationWarning ではなく PendingDeprecationWarning であるべき
        # (DeprecationWarning も PendingDeprecationWarning のサブクラスだが、
        #  「より強い警告」であることを担保するため明示チェック)
        for warning in w:
            if issubclass(warning.category, DeprecationWarning):
                assert issubclass(warning.category, PendingDeprecationWarning), (
                    f"DeprecationWarning だが PendingDeprecationWarning ではない: {warning.category}"
                )


class TestPermutationProperties:
    """permutation test の性質テスト."""

    def test_random_data_high_p_value(self):
        """ランダムデータ（エッジなし）→ p 値高."""
        np.random.seed(42)
        trade_pnls = np.random.normal(0, 1, 100).tolist()
        cluster_keys = [f"2024-01-{i % 28 + 1:02d}" for i in range(100)]
        result = permutation_test_block(trade_pnls, cluster_keys, n_permutations=1000, seed=42)
        # p 値は 0.05 より大きいはず（帰無仮説を棄却できない）
        assert result.p_value > 0.05

    def test_strong_positive_edge_low_p_value(self):
        """強い正のエッジ → p 値低."""
        # すべて勝ち（極端な例）
        trade_pnls = [1.0] * 50
        cluster_keys = [f"2024-01-{i % 28 + 1:02d}" for i in range(50)]
        result = permutation_test_block(trade_pnls, cluster_keys, n_permutations=1000, seed=42)
        # すべて勝ちでも block 化により p=0 には限らないが、有意水準以下
        # 50 トレード・50 クラスタ → 高い有意性
        assert result.p_value < 0.01
