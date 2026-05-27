import itertools
import numpy as np
from .backtest import run_backtest


PARAM_GRID = {
    "ma_crossover": {
        "fast_ma": {"values": [3, 5, 10, 15], "label": "快线周期"},
        "slow_ma": {"values": [10, 20, 30, 60], "label": "慢线周期"},
        "atr_stop_mult": {"values": [1.5, 2.0, 2.5, 3.0], "label": "ATR止损倍数"},
        "atr_take_mult": {"values": [2.0, 3.0, 4.0, 5.0], "label": "ATR止盈倍数"},
    },
    "dual_thrust": {
        "k": {"values": [0.3, 0.4, 0.5, 0.6, 0.7], "label": "K值(通道系数)"},
        "dual_thrust_hold": {"values": [2, 3, 5, 7], "label": "持有时长(天)"},
        "stop_loss_pct": {"values": [0.02, 0.03, 0.05], "label": "止损比例"},
        "take_profit_pct": {"values": [0.03, 0.05, 0.08], "label": "止盈比例"},
    },
    "heikin_ashi": {
        "atr_stop_mult": {"values": [1.5, 2.0, 2.5, 3.0], "label": "ATR止损倍数"},
        "atr_take_mult": {"values": [2.0, 3.0, 4.0, 5.0], "label": "ATR止盈倍数"},
    },
    "parabolic_sar": {
        "atr_stop_mult": {"values": [1.5, 2.0, 2.5, 3.0], "label": "ATR止损倍数"},
        "atr_take_mult": {"values": [2.0, 3.0, 4.0, 5.0], "label": "ATR止盈倍数"},
    },
}


def get_param_grid(strategy_name: str):
    return PARAM_GRID.get(strategy_name, {})


def optimize(close, high, low,
             initial_capital=10000,
             strategy_name="ma_crossover",
             trade_days=60,
             metric="sharpe_ratio") -> dict:
    grid = get_param_grid(strategy_name)
    if not grid:
        return {"error": f"策略 {strategy_name} 无优化参数"}

    param_names = list(grid.keys())
    param_values = [grid[p]["values"] for p in param_names]

    best_score = -np.inf
    best_params = None
    best_result = None
    all_results = []

    total = 1
    for v in param_values:
        total *= len(v)

    count = 0
    for combo in itertools.product(*param_values):
        kwargs = {param_names[i]: combo[i] for i in range(len(param_names))}
        kwargs["initial_capital"] = initial_capital
        kwargs["trade_days"] = trade_days
        kwargs["strategy_name"] = strategy_name
        kwargs["close"] = close
        kwargs["high"] = high
        kwargs["low"] = low

        atr_stop = kwargs.get("atr_stop_mult", 2.0)
        atr_take = kwargs.get("atr_take_mult", 3.0)
        kwargs["atr_stop_mult"] = atr_stop
        kwargs["atr_take_mult"] = atr_take

        try:
            result = run_backtest(**kwargs)
        except Exception:
            count += 1
            continue

        if "error" in result:
            count += 1
            continue

        score = result.get(metric, 0)
        if np.isnan(score) or score == float("inf") or score == float("-inf"):
            score = -999

        entry = {
            "params": {param_names[i]: combo[i] for i in range(len(param_names))},
            "metrics": {
                "total_return": result["total_return"],
                "sharpe_ratio": result["sharpe_ratio"],
                "max_drawdown": result["max_drawdown"],
                "win_rate": result["win_rate"],
                "profit_factor": result["profit_factor"],
                "win_loss_ratio": result["win_loss_ratio"],
                "total_trades": result["total_trades"],
                "final_capital": result["final_capital"],
            },
            "score": round(score, 4),
        }
        all_results.append(entry)

        if score > best_score:
            best_score = score
            best_params = {param_names[i]: combo[i] for i in range(len(param_names))}
            best_result = entry

        count += 1

    all_results.sort(key=lambda x: x["score"], reverse=True)
    top_n = [r for r in all_results[:10] if r["score"] > -999]

    return {
        "strategy": strategy_name,
        "metric": metric,
        "total_combinations": total,
        "tested": len(all_results),
        "best": best_result,
        "best_params": best_params,
        "top": top_n,
    }