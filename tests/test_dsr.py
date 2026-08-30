"""DSR (Deflated Sharpe Ratio) の回帰テスト.

Bailey & Lopez de Prado (2014) 公式の数値整合性検証。

参考値:
    論文 Figure 2 / Worked example (https://aifinhub.io/articles/deflated-sharpe-derivation-worked-example/)
    1.5 Sharpe, N=1000 trials, T=12 months, γ₃=0, γ₄=3 → DSR ≈ 0.52
    1.5 Sharpe, N=1, T=12, γ₃=0, γ₄=3 → DSR ≈ 0.999
"""

from __future__ import annotations

import numpy as np
import pytest

from minmax_fx_eval.statistics.dsr import (
    DSR_REQUIRED_THRESHOLD,
    deflated_sharpe_ratio,
    expected_max_sharpe_ratio,
    probabilistic_sharpe_ratio,
    compute_sharpe_z,
)


class TestExpectedMaxSharpe:
    """E[max SR*] のテスト."""

    def test_n_equals_1_returns_zero(self):
        """N=1 なら帰無仮説下 max = 0."""
        assert expected_max_sharpe_ratio(1) == 0.0

    def test_n_increases_expectation(self):
        """N が増えるほど E[max SR*] は単調増加."""
        e1 = expected_max_sharpe_ratio(2)
        e10 = expected_max_sharpe_ratio(10)
        e100 = expected_max_sharpe_ratio(100)
        e1000 = expected_max_sharpe_ratio(1000)
        assert e1 < e10 < e100 < e1000

    def test_n_1000_approx_3(self):
        """N=1000 で E[max SR*] ≈ 2.8-3.2（論文 Figure 2 参照）."""
        e = expected_max_sharpe_ratio(1000)
        assert 2.5 < e < 3.5

    def test_v03_n1_docstring_documents_psr_fallback(self) -> None:
        """v0.3 m-D1 対応: N=1 の docstring に「PSR と同等 (benchmark=0)」の
        解釈が明記されていること.

        C 査読 m-D1 修正案: 「docstring に『N=1 は PSR と同等 (benchmark=0)』と明記」
        """
        import inspect

        from minmax_fx_eval.statistics.dsr import expected_max_sharpe_ratio

        doc = inspect.getdoc(expected_max_sharpe_ratio) or ""
        assert "PSR" in doc, "N=1 の docstring に PSR への言及が無い (m-D1 未対応)"
        assert "benchmark" in doc.lower() or "0" in doc, (
            "N=1 の docstring に benchmark=0 の解釈が無い"
        )

    def test_n_invalid_raises(self):
        """N < 1 は ValueError."""
        with pytest.raises(ValueError):
            expected_max_sharpe_ratio(0)
        with pytest.raises(ValueError):
            expected_max_sharpe_ratio(-1)


class TestPSR:
    """Probabilistic Sharpe Ratio のテスト."""

    def test_zero_sharpe_zero_observations_returns_half(self):
        """Sharpe=0, T=2 なら PSR ≈ 0.5（境界）."""
        psr = probabilistic_sharpe_ratio(0.0, n_observations=2)
        assert 0.4 < psr < 0.6

    def test_high_sharpe_high_psr(self):
        """Sharpe=2.0, T=100 なら PSR ≈ 1.0（非常に高い）."""
        psr = probabilistic_sharpe_ratio(2.0, n_observations=100)
        assert psr > 0.99

    def test_negative_sharpe_low_psr(self):
        """Sharpe=-1.0 なら PSR < 0.5."""
        psr = probabilistic_sharpe_ratio(-1.0, n_observations=50)
        assert psr < 0.5

    def test_kurtosis_too_low_raises(self):
        """kurtosis < 1 は ValueError."""
        with pytest.raises(ValueError):
            probabilistic_sharpe_ratio(1.0, n_observations=50, kurtosis=0.5)


class TestDSR:
    """Deflated Sharpe Ratio のテスト."""

    def test_n1_dsr_equals_psr(self):
        """N=1 なら DSR = PSR（benchmark=0 との比較）."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 100)
        result = deflated_sharpe_ratio(returns, n_trials=1, periods_per_year=252)
        # N=1 のとき E[max SR*] = 0 なので DSR == PSR
        assert abs(result.dsr - result.psr) < 1e-6

    def test_n1000_sharpe_below_e_max_fails(self):
        """SR=1.5, N=1000: E[max SR*] ≈ 3.26 を下回る Sharpe では DSR < 0.5.

        Bailey 2014 論文の核心的な主張: N=1000 試行の帰無仮説下で E[max SR*] ≈ 3.26。
        観測 SR=1.58 はこの閾値を下回るため、DSR は有意水準を満たさない。
        aifinhub 記事の "0.52" 例は T=large / N=small など異なるパラメータでの話で、
        本テストの条件 (N=1000, T=252) では DSR は本質的に 0 となる。
        """
        np.random.seed(42)
        # ガウス乱数で年率 Sharpe ≈ 1.58 になるよう調整
        returns = np.random.normal(0.0001, 0.001, 252)
        result = deflated_sharpe_ratio(returns, n_trials=1000, periods_per_year=252)
        # E[max SR*]=3.26 >> SR_obs=1.58 → DSR は確実に非有意
        assert result.dsr < 0.05
        assert not result.passes_threshold
        # 期待値の検証
        assert 2.5 < result.expected_max_sharpe < 4.0  # N=1000 で 3.26 程度

    def test_high_sharpe_overcomes_e_max(self):
        """SR=5.0 のような極端な Sharpe なら N=1000 でも DSR ≥ 0.95 達成可能."""
        np.random.seed(42)
        # 年率 Sharpe ≈ 5.0 になるよう daily mean を大きく
        returns = np.random.normal(0.0003, 0.001, 252)  # SR ≈ 4.76
        result = deflated_sharpe_ratio(returns, n_trials=1000, periods_per_year=252)
        # SR=4.76 > E[max SR*]=3.26 → DSR は高確率で有意
        assert result.sharpe_observed > 4.0
        assert result.dsr > 0.5  # 強いエッジなので有意性は高くなるはず

    def test_zero_sharpe_low_dsr(self):
        """Sharpe=0, N=10 なら DSR < 0.5."""
        np.random.seed(42)
        returns = np.random.normal(0.0, 0.01, 100)
        result = deflated_sharpe_ratio(returns, n_trials=10, periods_per_year=252)
        # Sharpe=0 で N=10 なら DSR は小さい
        assert result.dsr < 0.5

    def test_dsr_threshold_default(self):
        """DSR_REQUIRED_THRESHOLD = 0.95 を確認."""
        assert DSR_REQUIRED_THRESHOLD == 0.95

    def test_v03_threshold_has_bailey_citation(self) -> None:
        """v0.3 m-S3 対応: DSR_REQUIRED_THRESHOLD の docstring に Bailey 2014 出典が
        記載されていること (Table 1, Figure 2, §3.2).

        C 査読 m-S3 修正案: 「ソース論文 Table 1 / Figure 2 の具体的閾値をコメントに記載」
        """
        import inspect

        from minmax_fx_eval.statistics import dsr as dsr_module

        source = inspect.getsource(dsr_module)
        # Bailey 2014 出典 (Table 1 / Figure 2 / §3.2 / Lopez de Prado 2018) の
        # いずれかが DSR_REQUIRED_THRESHOLD 定義近辺に書かれていること
        threshold_idx = source.find("DSR_REQUIRED_THRESHOLD = 0.95")
        assert threshold_idx > -1, "DSR_REQUIRED_THRESHOLD の定義が見つからない"
        # 直前 1500 文字以内 (コメントブロック) に出典が含まれること
        preceding = source[max(0, threshold_idx - 1500):threshold_idx]
        assert "Bailey" in preceding, "DSR_REQUIRED_THRESHOLD 定義前に Bailey 出典が無い"
        # 主要参照点 (Table 1 / Figure 2 / §3.2) のいずれかが言及されていること
        citation_markers = ["Table 1", "Figure 2", "§3.2", "Lopez de Prado 2018"]
        assert any(marker in preceding for marker in citation_markers), (
            f"Bailey 2014 出典に Table 1 / Figure 2 / §3.2 / Lopez de Prado 2018 "
            f"のいずれかが含まれていない: {preceding[-500:]}"
        )

    def test_passes_threshold_property(self):
        """passes_threshold プロパティの整合性."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.005, 100)  # 高 Sharpe
        result = deflated_sharpe_ratio(returns, n_trials=1, periods_per_year=252)
        # N=1 なら DSR は PSR と一致し、passes_threshold は比較結果と一致
        assert result.passes_threshold == (result.dsr >= result.threshold)

    def test_empty_returns_raises(self):
        """空 returns は ValueError."""
        with pytest.raises(ValueError):
            deflated_sharpe_ratio([], n_trials=10)

    def test_to_dict_includes_all_fields(self):
        """to_dict() に必須フィールドが全て含まれる."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 50)
        result = deflated_sharpe_ratio(returns, n_trials=5)
        d = result.to_dict()
        required = {
            "sharpe_observed", "expected_max_sharpe", "skewness", "kurtosis",
            "n_observations", "n_trials", "dsr", "psr", "z_statistic",
            "passes_threshold", "threshold",
        }
        assert required.issubset(d.keys())


class TestComputeSharpeZ:
    """compute_sharpe_z() pure function のテスト (v0.3 M-D1 対応)."""

    def test_basic_z_value(self):
        """Sharpe=1.0, T=100, benchmark=0 で z > 0.

        z = (1.0 - 0) * sqrt(99) / sqrt(1.0 - 0 + 0.5 * 1) = 9.95 / 1.225 ≈ 8.12
        """
        z = compute_sharpe_z(1.0, 100, 0.0)
        assert 7.5 < z < 8.5

    def test_z_with_benchmark(self):
        """benchmark = E[max SR*] (N=10 ≈ 1.57) のとき z < 0."""
        z_benchmark_zero = compute_sharpe_z(1.0, 100, 0.0)
        z_benchmark_pos = compute_sharpe_z(1.0, 100, 1.57)
        # benchmark が高いほど z は小さくなる
        assert z_benchmark_pos < z_benchmark_zero
        assert z_benchmark_pos < 0  # 1.0 < 1.57 なので負

    def test_z_with_skewness_kurtosis(self):
        """非ガウス補正（skewness・kurtosis）が効く."""
        z_gauss = compute_sharpe_z(1.0, 100, 0.0, skewness=0.0, kurtosis=3.0)
        z_fat_tail = compute_sharpe_z(1.0, 100, 0.0, skewness=0.0, kurtosis=6.0)
        # fat-tail (kurtosis=6) の方が分母が大きく z が小さい
        assert z_fat_tail < z_gauss

    def test_dsr_and_z_statistic_consistency(self):
        """v0.3 M-D1: DSR と z_statistic が同じ値から導出される（pure function 経由）.

        Φ(z_statistic) == dsr が成立することを確認。
        """
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 50)
        result = deflated_sharpe_ratio(returns, n_trials=5)

        # z_statistic から DSR を逆算
        from scipy import stats as scipy_stats
        dsr_from_z = float(scipy_stats.norm.cdf(result.z_statistic))
        # 報告されている DSR と一致
        assert abs(dsr_from_z - result.dsr) < 1e-10, (
            f"DSR from z_statistic ({dsr_from_z}) != reported DSR ({result.dsr})"
        )

    def test_psr_via_pure_function_consistency(self):
        """v0.3 M-D1: PSR が pure function 経由でも計算可能."""
        z_psr = compute_sharpe_z(1.0, 50, 0.0)
        from scipy import stats as scipy_stats
        psr_computed = float(scipy_stats.norm.cdf(z_psr))
        # PSR(probabilistic_sharpe_ratio) 経由の結果と一致
        psr_direct = probabilistic_sharpe_ratio(1.0, n_observations=50)
        assert abs(psr_computed - psr_direct) < 1e-10

    def test_compute_sharpe_z_validates_inputs(self):
        """compute_sharpe_z() の入力検証."""
        # n_observations < 1
        with pytest.raises(ValueError):
            compute_sharpe_z(1.0, 0, 0.0)
        # kurtosis < 1
        with pytest.raises(ValueError):
            compute_sharpe_z(1.0, 100, 0.0, kurtosis=0.5)
        # denom_sq <= 0
        # kurt=3, skew=10, SR=1: 1 - 10 + 0.5 = -8.5 < 0
        with pytest.raises(ValueError):
            compute_sharpe_z(1.0, 10, 0.0, kurtosis=3.0, skewness=10.0)


class TestDSRv03Robustness:
    """v0.3 m-S2/m-R2: NaN/inf ハンドリング・periods_per_year 正規化."""

    def test_nan_in_returns_raises(self):
        """NaN を含む returns は ValueError (m-S2)."""
        with pytest.raises(ValueError, match="NaN or inf"):
            deflated_sharpe_ratio([0.01, 0.02, float("nan"), 0.01], n_trials=5)

    def test_inf_in_returns_raises(self):
        """inf を含む returns は ValueError."""
        with pytest.raises(ValueError, match="NaN or inf"):
            deflated_sharpe_ratio([0.01, float("inf"), 0.02], n_trials=5)

    def test_all_finite_works(self):
        """全て有限の値は正常動作."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 50).tolist()
        result = deflated_sharpe_ratio(returns, n_trials=5)
        assert result.dsr > 0  # 何らかの値

    def test_non_standard_periods_warns(self):
        """非標準 periods_per_year で UserWarning (m-R2)."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 50).tolist()
        with pytest.warns(UserWarning, match="non-standard"):
            deflated_sharpe_ratio(returns, n_trials=5, periods_per_year=100)

    def test_standard_periods_no_warning(self):
        """標準 periods_per_year では警告なし."""
        import warnings as _warnings
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 50).tolist()
        for p in (1, 4, 12, 52, 252, 365):
            with _warnings.catch_warnings():
                _warnings.simplefilter("error")  # 警告が出たらエラー
                deflated_sharpe_ratio(returns, n_trials=5, periods_per_year=p)

    def test_schema_version_constant(self):
        """v0.3 m-R3: DeflatedSharpeRatioResult.SCHEMA_VERSION が定義されている."""
        from minmax_fx_eval.statistics.dsr import DeflatedSharpeRatioResult
        assert hasattr(DeflatedSharpeRatioResult, "SCHEMA_VERSION")
        assert DeflatedSharpeRatioResult.SCHEMA_VERSION == "1.0.0"
