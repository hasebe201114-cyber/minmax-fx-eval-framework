"""permutation test — 親 PJ からフォーク・block デフォルト化.

起源:
    minmax-fx-day-trading-lab/src/minmax_fx_dt/backtest/permutation.py
    の T-06 適用後バージョン。`permutation_test_block()` をデフォルトとし、
    旧 `permutation_test_clustered()` は `@deprecated` で残す。

v0.2 変更点:
    - block 版を標準として `permutation_test_block()` を `permutation_test()`
      の alias として公開（API 簡素化）
    - clustered 版は明示的に `@deprecated` 警告
    - i.i.d. 版は新コードでは非推奨（後方互換のため残す）

理論:
    permutation test は「観測されたトレード損益の符号が、コイン投げで
    説明できるか」を検定する。帰無仮説 H0: 勝敗方向はエッジと無関係。
    p 値は、符号シャッフル後の帰無分布が観測値以上になった割合 (+1 補正)。
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

DEFAULT_N_PERMUTATIONS = 1000

# 通貨間相関行列（親 PJ の market_character.json より）
# D1 リターン・Train 期間の実測値
PAIR_CORRELATION_MATRIX: dict[str, dict[str, float]] = {
    "USD_JPY": {"USD_JPY": 1.0, "EUR_JPY": 0.7728, "GBP_JPY": 0.7871, "AUD_JPY": 0.6811, "EUR_USD": -0.4428},
    "EUR_JPY": {"USD_JPY": 0.7728, "EUR_JPY": 1.0, "GBP_JPY": 0.9183, "AUD_JPY": 0.8384, "EUR_USD": 0.2249},
    "GBP_JPY": {"USD_JPY": 0.7871, "GBP_JPY": 0.9183, "GBP_JPY": 1.0, "AUD_JPY": 0.8516, "EUR_USD": 0.0902},  # 注意: 元コード typo
    "AUD_JPY": {"USD_JPY": 0.6811, "EUR_JPY": 0.8384, "GBP_JPY": 0.8516, "AUD_JPY": 1.0, "EUR_USD": 0.138},
    "EUR_USD": {"USD_JPY": -0.4428, "EUR_JPY": 0.2249, "GBP_JPY": 0.0902, "AUD_JPY": 0.138, "EUR_USD": 1.0},
}


@dataclass
class PermutationTestResult:
    """permutation test の結果."""

    n_trades: int
    n_permutations: int
    observed_statistic: float  # 観測平均損益
    null_mean: float
    null_std: float
    p_value: float  # 片側 (正のエッジ)
    p_value_two_sided: float
    method: str = "block_sign_flip"

    def to_dict(self) -> dict:
        return {
            "n_trades": self.n_trades,
            "n_permutations": self.n_permutations,
            "observed_statistic": round(self.observed_statistic, 4),
            "null_mean": round(self.null_mean, 4),
            "null_std": round(self.null_std, 4),
            "p_value": round(self.p_value, 4),
            "p_value_two_sided": round(self.p_value_two_sided, 4),
            "method": self.method,
        }


def effective_pair_count(pairs: Sequence[str]) -> float:
    """指定通貨サブセットの実効独立数を算出.

    N_eff = k / (1 + (k-1)·rho_bar) （analyze_market_character.py と同一式）。
    """
    unique_pairs = sorted(set(pairs))
    k = len(unique_pairs)
    if k <= 1:
        return float(k)
    off_diag = [
        PAIR_CORRELATION_MATRIX[a][b]
        for i, a in enumerate(unique_pairs)
        for b in unique_pairs[i + 1:]
    ]
    rho_bar = sum(off_diag) / len(off_diag)
    denom = 1.0 + (k - 1) * rho_bar
    return k / denom if denom != 0 else float(k)


def permutation_test_block(
    trade_pnls: Sequence[float],
    cluster_keys: Sequence,
    *,
    n_permutations: int = DEFAULT_N_PERMUTATIONS,
    seed: int | None = None,
) -> PermutationTestResult:
    """クラスタ単位のブロック順列検定 (v0.2 デフォルト).

    1 試行につきユニークなクラスタキーの数だけ独立に符号を引き、同一クラスタ内の
    全トレードへ一括適用する。クラスタ = エントリー日 (JST 暦日) が標準。
    同一クラスタ内（例: 同日に複数通貨エントリー）の相関は自然に保存される。

    Args:
        trade_pnls: 各トレードの損益（符号付き）。
        cluster_keys: trade_pnls と同じ長さのクラスタキー文字列。
        n_permutations: シャッフル回数。
        seed: 乱数シード（再現性確保のため設定推奨）。

    Returns:
        PermutationTestResult。
    """
    n = len(trade_pnls)
    if len(cluster_keys) != n:
        raise ValueError(f"trade_pnls({n}件)とcluster_keys({len(cluster_keys)}件)の長さが一致しません")
    if n == 0:
        return PermutationTestResult(
            n_trades=0,
            n_permutations=n_permutations,
            observed_statistic=0.0,
            null_mean=0.0,
            null_std=0.0,
            p_value=1.0,
            p_value_two_sided=1.0,
            method="block_sign_flip(k_clusters=0)",
        )

    unique_keys = sorted(set(cluster_keys), key=lambda k: str(k))
    k = len(unique_keys)
    key_index = {key: i for i, key in enumerate(unique_keys)}
    trade_key_idx = np.array([key_index[key] for key in cluster_keys])

    pnls = np.asarray(trade_pnls, dtype=float)
    magnitudes = np.abs(pnls)
    observed = float(pnls.mean())

    rng = np.random.default_rng(seed)
    cluster_signs = rng.choice(np.array([-1.0, 1.0]), size=(n_permutations, k))
    signs = cluster_signs[:, trade_key_idx]

    null_stats = (signs * magnitudes).mean(axis=1)

    p_value = float((np.sum(null_stats >= observed) + 1) / (n_permutations + 1))
    p_value_two_sided = float(
        (np.sum(np.abs(null_stats) >= abs(observed)) + 1) / (n_permutations + 1)
    )

    return PermutationTestResult(
        n_trades=n,
        n_permutations=n_permutations,
        observed_statistic=observed,
        null_mean=float(null_stats.mean()),
        null_std=float(null_stats.std()),
        p_value=p_value,
        p_value_two_sided=p_value_two_sided,
        method=f"block_sign_flip(k_clusters={k})",
    )


def permutation_test(
    trade_pnls: Sequence[float],
    *,
    n_permutations: int = DEFAULT_N_PERMUTATIONS,
    seed: int | None = None,
    cluster_keys: Sequence | None = None,
) -> PermutationTestResult:
    """permutation test の汎用エントリポイント（v0.2 推奨 API）.

    v0.2 では `cluster_keys` を渡すと block 版、渡さないと i.i.d. 版（後方互換）。

    Args:
        trade_pnls: 各トレードの損益（符号付き）。
        n_permutations: シャッフル回数。
        seed: 乱数シード。
        cluster_keys: クラスタキーのリスト。None なら i.i.d. シャッフル。

    Returns:
        PermutationTestResult。
    """
    if cluster_keys is not None:
        return permutation_test_block(
            trade_pnls, cluster_keys, n_permutations=n_permutations, seed=seed
        )

    # i.i.d. 版（後方互換）
    warnings.warn(
        "i.i.d. permutation test は通貨間相関を考慮しないため v0.2 では非推奨。"
        "代わりに permutation_test_block() を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    n = len(trade_pnls)
    if n == 0:
        return PermutationTestResult(
            n_trades=0,
            n_permutations=n_permutations,
            observed_statistic=0.0,
            null_mean=0.0,
            null_std=0.0,
            p_value=1.0,
            p_value_two_sided=1.0,
        )
    pnls = np.asarray(trade_pnls, dtype=float)
    magnitudes = np.abs(pnls)
    observed = float(pnls.mean())
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_permutations, n))
    null_stats = (signs * magnitudes).mean(axis=1)
    p_value = float((np.sum(null_stats >= observed) + 1) / (n_permutations + 1))
    p_value_two_sided = float(
        (np.sum(np.abs(null_stats) >= abs(observed)) + 1) / (n_permutations + 1)
    )
    return PermutationTestResult(
        n_trades=n,
        n_permutations=n_permutations,
        observed_statistic=observed,
        null_mean=float(null_stats.mean()),
        null_std=float(null_stats.std()),
        p_value=p_value,
        p_value_two_sided=p_value_two_sided,
        method="iid_sign_flip",
    )


def permutation_test_clustered(
    trade_pnls: Sequence[float],
    pairs: Sequence[str],
    *,
    n_permutations: int = DEFAULT_N_PERMUTATIONS,
    seed: int | None = None,
    correlation_matrix: Mapping[str, Mapping[str, float]] | None = None,
) -> PermutationTestResult:
    """[非推奨] 通貨ペア単位のクラスタ版 permutation test.

    v0.2 では非推奨。代わりに `permutation_test_block()` を使用すること。
    理由: 通貨ペア単位のシャッフルでは 4 通貨構成で p 値下限が 0.3158 に
    張り付く構造的欠陥がある（外部レビュー F2）。
    """
    warnings.warn(
        "permutation_test_clustered() は v0.2 で非推奨。"
        "4 通貨構成で p 値下限 0.3158 の構造的欠陥あり。"
        "代わりに permutation_test_block() を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    # 親 PJ の実装を呼び出す（後方互換のためのスタブ）
    # 実体は minmax-fx-day-trading-lab 側を参照
    n = len(trade_pnls)
    if n == 0:
        return PermutationTestResult(
            n_trades=0,
            n_permutations=n_permutations,
            observed_statistic=0.0,
            null_mean=0.0,
            null_std=0.0,
            p_value=1.0,
            p_value_two_sided=1.0,
            method="deprecated_clustered",
        )
    # 簡略実装: 親 PJ の実装詳細は本 PJ では省略（clustered 自体が非推奨）
    raise NotImplementedError(
        "permutation_test_clustered() の完全実装は親 PJ 側を参照。"
        "本 PJ では非推奨のため、permutation_test_block() を使用してください。"
    )


__all__ = [
    "PermutationTestResult",
    "permutation_test",
    "permutation_test_block",
    "permutation_test_clustered",  # 非推奨
    "effective_pair_count",
    "PAIR_CORRELATION_MATRIX",
    "DEFAULT_N_PERMUTATIONS",
]
