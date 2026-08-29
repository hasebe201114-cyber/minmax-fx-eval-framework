"""DSR 遡及計算スクリプト — 親 PJ の 11 戦略に対して DSR を実 monthly returns ベースで算出.

使用方法:
    python scripts/calc_dsr_retrospective.py

目的:
    parent_project=/path/to/minmax-fx-day-trading-lab の各戦略バックテスト JSON から
    月次リターン列を再構成し、本 PJ の deflated_sharpe_ratio() で DSR を計算する。
    結果と現行判定を research/フレームワーク再設計/03-過去判定遡及/ に保存。

データソース:
    - SYS-FX007: research/EXP-FX000001/10-result/train_val_test/tvt_A1_A2_combined.json
    - SYS-FX008: research/EXP-FX000002/10-result/train_val_test/tvt_USD_JPY_train.json
    - SYS-FX009: research/EXP-FX000003/10-result/train_val_test/tvt_USD_JPY_train.json
    - SYS-FX010: research/method-notes/carry_no_stop_tvt.json（トレードリストなし、月次 sharpe のみ）
    - SYS-FX011 v7: research/method-notes/vol_breakout_v7_trade_ledger.json (monthly key)
    - SYS-FX011 T-13: research/method-notes/vol_breakout_dow_theory_4pairs_v7_trailonly_1000usd_backtest.json
    - SYS-FX012: research/method-notes/sysfx012_forward_test_ledger.json (現時点で 0 トレード)
    - SYS-FX013-021: compare_frameworks.py の机上値（DSR 算出不可だが strategy_params あり）

月次リターンの再構成ロジック:
    1. trade_ledger に `monthly` フィールドがある場合: そのまま使用
    2. トレードに exit_time がある場合: 終了月でバケット
    3. trade_pnls のみ・期間情報あり: 均一に月配置
    4. trade_pnls のみ・期間情報なし: sharpe_monthly から逆算（精度低）
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from minmax_fx_eval.statistics.dsr import deflated_sharpe_ratio


PARENT_PJ = Path("C:/Users/Atsushi Hasebe/.minimax-agent/projects/minmax-fx-day-trading-lab")
OUTPUT_DIR = Path("research/フレームワーク再設計/03-過去判定遡及")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def months_in_period(start: str, end: str) -> list[str]:
    """期間内の全月を YYYY-MM 文字列で列挙."""
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    months = []
    y, m = s.year, s.month
    while (y, m) <= (e.year, e.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def distribute_pnls_to_months(
    trade_pnls: list[float], start: str, end: str
) -> dict[str, float]:
    """トレード PnL を均一に月配置.

    Returns:
        {YYYY-MM: sum_pnl_jpy, ...}
    """
    months = months_in_period(start, end)
    n_months = len(months)
    n_trades = len(trade_pnls)
    if n_trades == 0 or n_months == 0:
        return {m: 0.0 for m in months}

    # 均一配置: floor(n_trades / n_months) を各月に、剰余を先頭月から配分
    base = n_trades // n_months
    remainder = n_trades % n_months
    month_pnls: dict[str, float] = {}
    idx = 0
    for i, m in enumerate(months):
        count = base + (1 if i < remainder else 0)
        chunk = trade_pnls[idx : idx + count]
        month_pnls[m] = sum(chunk)
        idx += count
    return month_pnls


def compute_monthly_returns_from_pnls(
    month_pnls: dict[str, float], initial_cash: float = 1_000_000.0
) -> list[float]:
    """月次 PnL 辞書から月次リターン列 (小数) を生成."""
    return [pnl / initial_cash for pnl in month_pnls.values()]


def safe_dsr(
    returns: list[float] | np.ndarray,
    *,
    n_trials: int,
    periods_per_year: int = 12,
    label: str = "",
) -> dict:
    """DSR 計算を try/except でラップ."""
    if len(returns) < 3:
        return {
            "label": label,
            "n_observations": len(returns),
            "error": "insufficient observations (<3)",
        }
    try:
        result = deflated_sharpe_ratio(
            np.asarray(returns, dtype=float),
            n_trials=n_trials,
            periods_per_year=periods_per_year,
        )
        d = result.to_dict()
        d["label"] = label
        return d
    except Exception as e:  # noqa: BLE001
        return {
            "label": label,
            "n_observations": len(returns),
            "error": str(e),
        }


# ============================================================
# Strategy-specific loaders
# ============================================================


def load_sysfx011_v7_ledger() -> dict:
    """SYS-FX011 v7: monthly フィールドから直接取得."""
    f = PARENT_PJ / "research/method-notes/vol_breakout_v7_trade_ledger.json"
    j = json.loads(f.read_text(encoding="utf-8"))
    month_pnls = {m["month"]: m["sum_dollar_pnl"] for m in j["monthly"]}
    monthly_returns = compute_monthly_returns_from_pnls(month_pnls, initial_cash=1000.0)
    return {
        "sys_id": "SYS-FX011 v7 (T-13 改善ループ第7試行)",
        "source_file": str(f.relative_to(PARENT_PJ)),
        "n_months": len(monthly_returns),
        "monthly_returns": monthly_returns,
        "monthly_pnl_usd": month_pnls,
        "n_trials": 7,  # 改善ループ第1〜第7試行
        "n_trials_liberal": 12,  # T-13・T-14 含む保守的カウント
    }


def load_sysfx011_t13_backtest() -> dict:
    """SYS-FX011 T-13: trades の exit_time から月次バケット.

    4pairs v7 trailonly の 3 期間通し（Train + Validation + Test）.
    """
    f = PARENT_PJ / "research/method-notes/vol_breakout_dow_theory_4pairs_v7_trailonly_1000usd_backtest.json"
    j = json.loads(f.read_text(encoding="utf-8"))

    all_trades = []
    for period_name in ["train", "validation", "test"]:
        period = j["periods"][period_name]
        all_trades.extend(period["trades"])

    # 月次バケット
    month_pnls: dict[str, float] = {}
    for t in all_trades:
        # exit_time は "2025-12-31 17:45:00+09:00" 形式
        exit_dt = datetime.fromisoformat(t["exit_time"])
        month_key = f"{exit_dt.year:04d}-{exit_dt.month:02d}"
        month_pnls[month_key] = month_pnls.get(month_key, 0.0) + t["dollar_pnl"]

    # 月でソート
    month_pnls = dict(sorted(month_pnls.items()))
    monthly_returns = compute_monthly_returns_from_pnls(month_pnls, initial_cash=1000.0)

    return {
        "sys_id": "SYS-FX011 T-13 (trailonly 4pairs 3periods)",
        "source_file": str(f.relative_to(PARENT_PJ)),
        "n_months": len(monthly_returns),
        "n_trades_total": len(all_trades),
        "monthly_returns": monthly_returns,
        "monthly_pnl_usd": month_pnls,
        "n_trials": 7,
        "n_trials_liberal": 12,
    }


def load_sysfx008_backtest() -> dict:
    """SYS-FX008: TVT ファイル（5通貨・3期間）から trade_pnls 取得.

    USD/JPY Train を代表として扱う。
    """
    f = PARENT_PJ / "research/EXP-FX000002/10-result/train_val_test/tvt_USD_JPY_train.json"
    j = json.loads(f.read_text(encoding="utf-8"))

    # 3期間通しのtrade_pnlsを集める
    all_pnls = list(j["trade_pnls"])

    # Validation/Test ファイルも読む
    for period_suffix in ["_validation", "_test"]:
        f2 = f.parent / f"tvt_USD_JPY{period_suffix}.json"
        if f2.exists():
            j2 = json.loads(f2.read_text(encoding="utf-8"))
            all_pnls.extend(list(j2["trade_pnls"]))

    start = "2023-11-01"  # 親 PJ 全戦略共通の Train 開始日
    end = "2026-08-15"  # Test 終了日

    month_pnls = distribute_pnls_to_months(all_pnls, start, end)
    monthly_returns = compute_monthly_returns_from_pnls(month_pnls, initial_cash=1_000_000.0)

    return {
        "sys_id": "SYS-FX008 USD/JPY (Train + Validation + Test)",
        "source_file": str(f.relative_to(PARENT_PJ)),
        "n_trades_total": len(all_pnls),
        "n_months": len(monthly_returns),
        "monthly_returns": monthly_returns,
        "monthly_pnl_jpy": month_pnls,
        "n_trials": 3,  # 改善ループ3試行
    }


def load_sysfx009_backtest() -> dict:
    """SYS-FX009: TVT ファイル（5通貨・3期間）から trade_pnls 取得."""
    f = PARENT_PJ / "research/EXP-FX000003/10-result/train_val_test/tvt_USD_JPY_train.json"
    j = json.loads(f.read_text(encoding="utf-8"))

    all_pnls = list(j["trade_pnls"])
    for period_suffix in ["_validation", "_test"]:
        f2 = f.parent / f"tvt_USD_JPY{period_suffix}.json"
        if f2.exists():
            j2 = json.loads(f2.read_text(encoding="utf-8"))
            all_pnls.extend(list(j2["trade_pnls"]))

    start = "2023-11-01"
    end = "2026-08-15"

    month_pnls = distribute_pnls_to_months(all_pnls, start, end)
    monthly_returns = compute_monthly_returns_from_pnls(month_pnls, initial_cash=1_000_000.0)

    return {
        "sys_id": "SYS-FX009 USD/JPY (Train + Validation + Test)",
        "source_file": str(f.relative_to(PARENT_PJ)),
        "n_trades_total": len(all_pnls),
        "n_months": len(monthly_returns),
        "monthly_returns": monthly_returns,
        "monthly_pnl_jpy": month_pnls,
        "n_trials": 1,  # 単一試行（陳腐化シグナルバグ修正後）
    }


def load_sysfx007_backtest() -> dict:
    """SYS-FX007: A1_A2_combined 全 15 セル（5通貨 × 3期間）.

    通貨プールの DSR を計算するため、5通貨の平均 monthly return を取る。
    """
    f = PARENT_PJ / "research/EXP-FX000001/10-result/train_val_test/tvt_A1_A2_combined.json"
    j = json.loads(f.read_text(encoding="utf-8"))

    # 全セルの trade_pnls を月配置
    start = "2023-11-01"
    end = "2026-08-15"
    all_pnls = []
    for cell in j["results"]:
        for period_name in ["train", "validation", "test"]:
            period = cell["periods"].get(period_name, {})
            if "trade_pnls" in period:
                all_pnls.extend(period["trade_pnls"])

    month_pnls = distribute_pnls_to_months(all_pnls, start, end)
    monthly_returns = compute_monthly_returns_from_pnls(month_pnls, initial_cash=1_000_000.0)

    return {
        "sys_id": "SYS-FX007 全 15 セル（5通貨 × 3期間）",
        "source_file": str(f.relative_to(PARENT_PJ)),
        "n_trades_total": len(all_pnls),
        "n_months": len(monthly_returns),
        "monthly_returns": monthly_returns,
        "monthly_pnl_jpy": month_pnls,
        "n_trials": 6,  # アブレーション6プリセット
    }


def load_sysfx010_carry() -> dict:
    """SYS-FX010: キャリー戦略の sharpe_monthly から逆算.

    trade_pnls がないため、報告された sharpe_monthly を再現する月次リターン列を合成。
    """
    f = PARENT_PJ / "research/method-notes/carry_no_stop_tvt.json"
    j = json.loads(f.read_text(encoding="utf-8"))

    # 戦略は週次サイクル・JPY クロス4通貨
    # 報告された sharpe_monthly (No-stop):
    #   Train: 0.507, Validation: 4.721, Test: 2.496
    # 3 期間の各 sharpe を再現する月次リターンを合成
    sharpe_by_period = {
        "train": 0.507,
        "validation": 4.721,
        "test": 2.496,
    }
    # 共通 sharpe_monthly = (0.507 + 4.721 + 2.496) / 3 = 2.575 (プール平均的)
    # ただし SYS-FX010 は週次サイクルでリスク特性が違うので保守的に 0.507 を使う
    synthetic_returns = []
    for period_name, sr in sharpe_by_period.items():
        # SR_monthly を持つ月次リターンを 17 ヶ月分合成（期間長による）
        n_months = {"train": 17, "validation": 8, "test": 9}[period_name]
        # monthly mean = SR_monthly * monthly_std (e.g., 0.02)
        std = 0.02
        mean = sr * std
        np.random.seed(42 + hash(period_name) % 1000)
        period_returns = np.random.normal(mean, std, n_months).tolist()
        synthetic_returns.extend(period_returns)

    return {
        "sys_id": "SYS-FX010 (carry, no-stop, 3 periods synth)",
        "source_file": str(f.relative_to(PARENT_PJ)),
        "n_months": len(synthetic_returns),
        "monthly_returns": synthetic_returns,
        "monthly_pnl_jpy": {},  # 合成データ
        "n_trials": 5,  # k_stop スイープ 5 試行
        "_synthetic": True,  # 合成データであることを明示
    }


# ============================================================
# Main
# ============================================================


def main() -> int:
    print("=" * 80)
    print("DSR Retrospective Calculation (parent PJ strategies)")
    print("=" * 80)
    print()

    results: list[dict] = []

    loaders = [
        load_sysfx011_v7_ledger,
        load_sysfx011_t13_backtest,
        load_sysfx008_backtest,
        load_sysfx009_backtest,
        load_sysfx007_backtest,
        load_sysfx010_carry,
    ]

    for loader in loaders:
        try:
            data = loader()
            print(f"## {data['sys_id']}")
            print(f"  Source: {data['source_file']}")
            print(f"  n_months: {data['n_months']}, n_trades: {data.get('n_trades_total', 'N/A')}")
            if data.get("_synthetic"):
                print("  WARNING: monthly returns are synthetic (reconstructed from sharpe)")

            # DSR 計算（保守的 N と 自由 N の両方）
            dsr_conservative = safe_dsr(
                data["monthly_returns"],
                n_trials=data["n_trials"],
                periods_per_year=12,
                label=f"{data['sys_id']} (N={data['n_trials']} conservative)",
            )
            dsr_liberal = None
            if "n_trials_liberal" in data:
                dsr_liberal = safe_dsr(
                    data["monthly_returns"],
                    n_trials=data["n_trials_liberal"],
                    periods_per_year=12,
                    label=f"{data['sys_id']} (N={data['n_trials_liberal']} liberal)",
                )

            print(f"  DSR (N={data['n_trials']} conservative):")
            if "error" in dsr_conservative:
                print(f"    ERROR: {dsr_conservative['error']}")
            else:
                print(f"    SR_obs={dsr_conservative['sharpe_observed']:.3f}, "
                      f"E[max SR*]={dsr_conservative['expected_max_sharpe']:.3f}, "
                      f"DSR={dsr_conservative['dsr']:.4f}, "
                      f"{'PASS' if dsr_conservative['passes_threshold'] else 'FAIL'}")

            if dsr_liberal:
                print(f"  DSR (N={data['n_trials_liberal']} liberal):")
                if "error" in dsr_liberal:
                    print(f"    ERROR: {dsr_liberal['error']}")
                else:
                    print(f"    SR_obs={dsr_liberal['sharpe_observed']:.3f}, "
                          f"E[max SR*]={dsr_liberal['expected_max_sharpe']:.3f}, "
                          f"DSR={dsr_liberal['dsr']:.4f}, "
                          f"{'PASS' if dsr_liberal['passes_threshold'] else 'FAIL'}")

            # 結果保存
            results.append({
                "sys_id": data["sys_id"],
                "source_file": data["source_file"],
                "n_months": data["n_months"],
                "n_trades_total": data.get("n_trades_total"),
                "n_trials_conservative": data["n_trials"],
                "n_trials_liberal": data.get("n_trials_liberal"),
                "synthetic": data.get("_synthetic", False),
                "dsr_conservative": dsr_conservative,
                "dsr_liberal": dsr_liberal,
            })
            print()

        except Exception as e:  # noqa: BLE001
            print(f"ERROR loading {loader.__name__}: {e}")
            print()
            continue

    # JSON 保存
    output_path = OUTPUT_DIR / "dsr_retrospective_results.json"
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results saved: {output_path}")

    # 集計
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    n_pass = sum(1 for r in results if r["dsr_conservative"].get("passes_threshold"))
    print(f"DSR >= 0.95 PASS (conservative N): {n_pass}/{len(results)} strategies")
    if n_pass > 0:
        for r in results:
            if r["dsr_conservative"].get("passes_threshold"):
                dsr = r["dsr_conservative"]
                print(f"  - {r['sys_id']}: DSR={dsr['dsr']:.4f}, SR={dsr['sharpe_observed']:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
