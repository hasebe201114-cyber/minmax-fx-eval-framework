"""統計検定モジュール."""

from .dsr import (
    DeflatedSharpeRatioResult,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    expected_max_sharpe_ratio,
    compute_sharpe_z,
)
from .n_trials_counter import (
    NTrialsBreakdown,
    count_n_trials,
    KNOWN_STRATEGY_N_TRIALS,
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
    "compute_sharpe_z",
    # n_trials
    "NTrialsBreakdown",
    "count_n_trials",
    "KNOWN_STRATEGY_N_TRIALS",
    # permutation
    "PermutationTestResult",
    "permutation_test_block",
    "effective_pair_count",
    # power
    "minimum_sample_size_for_power",
    "power_analysis",
]
