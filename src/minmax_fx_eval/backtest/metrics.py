"""バックテスト KPI 計算 — 親 PJ の metrics.py をフォーク.

起源:
    minmax-fx-day-trading-lab/src/minmax_fx_dt/backtest/metrics.py

本 PJ では K1m〜K7m 計算に必要な部分のみを残す。PortfolioState/Trade 等の
バックテストエンジン型は親 PJ の simulator.py に依存するため、
本 PJ では receive せず、必要なら呼び出し側で `compute_metrics_simple()` 等を使う。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestMetrics:
    """バックテスト KPI（最小実装）."""

    sharpe_monthly: float
    sharpe_yearly: float
    profit_factor_monthly: float
    profit_factor_yearly: float
    expectancy_jpy: float
    max_dd_jpy: float
    max_dd_monthly_pct: float
    max_dd_yearly_pct: float
    max_consecutive_losses: int
    payoff_ratio: float
    n_trades: int
    n_wins: int
    n_losses: int
    win_rate: float
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    equity_curve: pd.DataFrame


def profit_factor(trade_pnls: list[float]) -> float:
    """Profit Factor = 総利益 / 総損失(絶対値)."""
    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss = abs(sum(p for p in trade_pnls if p < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def payoff_ratio(trade_pnls: list[float]) -> float:
    """ペイオフレシオ = 平均利益 / 平均損失(絶対値)."""
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    if not wins or not losses:
        return 0.0
    avg_win = sum(wins) / len(wins)
    avg_loss = abs(sum(losses) / len(losses))
    if avg_loss == 0:
        return float("inf")
    return avg_win / avg_loss


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252, risk_free: float = 0.0) -> float:
    """年率シャープレシオ."""
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free
    if excess.std() == 0 or np.isnan(excess.std()):
        return 0.0
    return float(excess.mean() / excess.std() * math.sqrt(periods_per_year))


def monthly_sharpe(equity_curve: pd.DataFrame) -> float:
    """月次シャープレシオ（K1m）."""
    if len(equity_curve) < 2:
        return 0.0
    eq = equity_curve.set_index("timestamp")["equity"].resample("ME").last()
    monthly_returns = eq.pct_change().dropna()
    if len(monthly_returns) < 2:
        return 0.0
    if monthly_returns.std() == 0:
        return 0.0
    return float(monthly_returns.mean() / monthly_returns.std() * math.sqrt(12))


def max_drawdown(equity_curve: pd.DataFrame) -> tuple[float, float]:
    """最大 DD（JPY・初期資金比 %）.

    固定ロットサイジングの戦略のみ。複利の場合は peak_relative_max_dd_pct を使う。
    """
    if len(equity_curve) < 2:
        return 0.0, 0.0
    eq = equity_curve["equity"].to_numpy()
    running_max = np.maximum.accumulate(eq)
    drawdown = running_max - eq
    max_dd_jpy = float(drawdown.max()) if len(drawdown) > 0 else 0.0
    initial = eq[0] if len(eq) > 0 else 1.0
    max_dd_pct = (max_dd_jpy / initial) * 100.0 if initial > 0 else 0.0
    return max_dd_jpy, max_dd_pct


def peak_relative_max_dd_pct(equity_curve: pd.DataFrame) -> float:
    """最大 DD（直近ピーク比 %）— 複利サイジング戦略向け."""
    if len(equity_curve) < 2:
        return 0.0
    eq = equity_curve.set_index("timestamp")["equity"]
    running_max = eq.cummax()
    dd = (running_max - eq) / running_max * 100.0
    return float(dd.max()) if len(dd) > 0 else 0.0


def compute_metrics(
    trade_pnls: list[float],
    equity_curve: pd.DataFrame,
    initial_cash: float = 1_000_000.0,
    win_trades: int | None = None,
    loss_trades: int | None = None,
    max_consecutive_losses: int | None = None,
) -> BacktestMetrics:
    """トレード PnL 列とエクイティカーブから KPI を計算（シンプル版）.

    親 PJ の PortfolioState 経由ではなく、リスト・DataFrame を直接渡す版。
    親 PJ の compute_metrics() は PortfolioState.trade_history から抽出するため
    依存が増えるが、本 PJ では最小限の依存で動く版を提供。

    Args:
        trade_pnls: 各トレードの損益（円）。
        equity_curve: timestamp・equity 列を持つ DataFrame。
        initial_cash: 初期資金（DD% 計算用）。
        win_trades: 勝ちトレード数（None なら自動カウント）。
        loss_trades: 負けトレード数（None なら自動カウント）。
        max_consecutive_losses: 最大連続損失数（None なら自動カウント）。

    Returns:
        BacktestMetrics。
    """
    pnls = list(trade_pnls)

    # 勝敗カウント
    if win_trades is None or loss_trades is None:
        win_trades = sum(1 for p in pnls if p > 0)
        loss_trades = sum(1 for p in pnls if p < 0)

    # 最大連続損失
    if max_consecutive_losses is None:
        flags = [p < 0 for p in pnls]
        cur = best = 0
        for f in flags:
            cur = cur + 1 if f else 0
            best = max(best, cur)
        max_consecutive_losses = best

    # 期間
    if not equity_curve.empty:
        period_start = equity_curve["timestamp"].iloc[0]
        period_end = equity_curve["timestamp"].iloc[-1]
    else:
        period_start = pd.Timestamp("2000-01-01")
        period_end = pd.Timestamp("2000-01-01")

    return BacktestMetrics(
        sharpe_monthly=monthly_sharpe(equity_curve),
        sharpe_yearly=sharpe_ratio(equity_curve.set_index("timestamp")["equity"].pct_change().dropna()),
        profit_factor_monthly=profit_factor(pnls),
        profit_factor_yearly=profit_factor(pnls),
        expectancy_jpy=sum(pnls) / len(pnls) if pnls else 0.0,
        max_dd_jpy=max_drawdown(equity_curve)[0],
        max_dd_monthly_pct=max_drawdown(equity_curve)[1],
        max_dd_yearly_pct=max_drawdown(equity_curve)[1],
        max_consecutive_losses=max_consecutive_losses,
        payoff_ratio=payoff_ratio(pnls),
        n_trades=len(pnls),
        n_wins=win_trades,
        n_losses=loss_trades,
        win_rate=win_trades / max(1, len(pnls)) * 100.0,
        period_start=period_start,
        period_end=period_end,
        equity_curve=equity_curve,
    )


__all__ = [
    "BacktestMetrics",
    "profit_factor",
    "payoff_ratio",
    "sharpe_ratio",
    "monthly_sharpe",
    "max_drawdown",
    "peak_relative_max_dd_pct",
    "compute_metrics",
]
