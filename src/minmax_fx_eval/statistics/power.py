"""検出力分析 (Power Analysis) — 親 PJ では MIN_N_TRADES_STATISTICAL = 300 ハードコード.

起源:
    minmax-fx-day-trading-lab/src/minmax_fx_dt/decision/criteria.py:75
    「旧値 60→66 は統計的な検出力計算に基づくものではなく、(1) 60 は初期 spec の
    経験則的な値、(2) 66 は SYS-FX007 ベースラインプリセットの Train 実測トレード数が
    たまたま 66 件だった」という経緯があり、permutation test 検出力シミュレーションで
    300 を再導出した（scripts/derive_min_n_trades_power.py）。

v0.2 変更点:
    - 動的検出力計算: 想定エッジ強度（勝率 or Sharpe）・有意水準・検出力から
      必要最小サンプル数を算出
    - 親 PJ の固定 300 は DSR で動的補正されるため安全弁（n ≥ 50 hard floor）として残す
    - 本モジュールは CLI からの検事前計算用ユーティリティ
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class PowerAnalysisResult:
    """検出力分析の結果."""

    effect_size: float
    alpha: float
    power: float
    n_required: int
    n_actual: int
    power_actual: float

    def to_dict(self) -> dict:
        return {
            "effect_size": round(self.effect_size, 4),
            "alpha": self.alpha,
            "power_target": self.power,
            "n_required": self.n_required,
            "n_actual": self.n_actual,
            "power_actual": round(self.power_actual, 4),
        }


def minimum_sample_size_for_power(
    effect_size: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = False,
) -> int:
    """検定力 1-β を達成する最小サンプル数を算出する（片側 or 両側 t 検定近似）.

    Args:
        effect_size: Cohen's d 相当（mean / std）。例: 勝率 60% vs 50% なら
            effect_size = 0.2 程度（hits - misses = 0.1、std = 0.5 より）。
        alpha: 有意水準（デフォルト 0.05）。
        power: 目標検定力（デフォルト 0.80）。
        two_sided: 両側検定なら True、片側なら False（デフォルト）。

    Returns:
        必要最小サンプル数（int）。

    Note:
        親 PJ の scripts/derive_min_n_trades_power.py と論理的に同等だが、
        scipy 経由でより正確な計算を行う。
    """
    if effect_size <= 0:
        raise ValueError(f"effect_size must be > 0, got {effect_size}")
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    if not 0 < power < 1:
        raise ValueError(f"power must be in (0, 1), got {power}")

    # 臨界値
    if two_sided:
        z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)
    else:
        z_alpha = stats.norm.ppf(1.0 - alpha)
    z_beta = stats.norm.ppf(power)

    # 漸近公式: n = ((z_alpha + z_beta) / effect_size)²
    n = math.ceil(((z_alpha + z_beta) / effect_size) ** 2)
    return int(n)


def power_analysis(
    n: int,
    effect_size: float,
    *,
    alpha: float = 0.05,
    two_sided: bool = False,
) -> PowerAnalysisResult:
    """与えられた n・effect_size・alpha で達成される検定力を算出.

    Args:
        n: サンプルサイズ。
        effect_size: Cohen's d 相当。
        alpha: 有意水準。
        two_sided: 両側検定か。

    Returns:
        PowerAnalysisResult。power_actual は観測された検定力。
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    if effect_size <= 0:
        raise ValueError(f"effect_size must be > 0, got {effect_size}")

    # 必要 n
    n_required = minimum_sample_size_for_power(
        effect_size, alpha=alpha, power=0.80, two_sided=two_sided
    )

    # 観測された検定力
    if two_sided:
        z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)
    else:
        z_alpha = stats.norm.ppf(1.0 - alpha)

    se = 1.0 / math.sqrt(n)
    z_beta = effect_size * math.sqrt(n) - z_alpha
    power_actual = float(stats.norm.cdf(z_beta))

    return PowerAnalysisResult(
        effect_size=effect_size,
        alpha=alpha,
        power=0.80,
        n_required=n_required,
        n_actual=n,
        power_actual=power_actual,
    )


__all__ = [
    "PowerAnalysisResult",
    "minimum_sample_size_for_power",
    "power_analysis",
]
