"""統計検定モジュール."""

from .dsr import (
    DeflatedSharpeRatioResult,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    expected_max_sharpe_ratio,
)
from .permutation import (
    PermutationTestResult,
    permutation_test_block,
    effective_pair_count,
)
from .power import (
    minimum_sample_size_for_power,
    power_analysis,
)

__all__ = [
    # DSR
    "DeflatedSharpeRatioResult",
    "deflated_sharpe_ratio",
    "probabilistic_sharpe_ratio",
    "expected_max_sharpe_ratio",
    # permutation
    "PermutationTestResult",
    "permutation_test_block",
    "effective_pair_count",
    # power
    "minimum_sample_size_for_power",
    "power_analysis",
]
