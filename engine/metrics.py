import numpy as np
import pandas as pd


def calculate_metrics(equity_curve: pd.Series) -> dict:
    if equity_curve.empty or len(equity_curve) < 2:
        return {}

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    daily_returns = equity_curve.pct_change().dropna()

    if len(daily_returns) == 0:
        return {"总收益率": f"{total_return:.2%}"}

    annual_return = (1 + total_return) ** (252 / len(daily_returns)) - 1
    volatility = daily_returns.std() * np.sqrt(252)
    sharpe = (annual_return - 0.03) / volatility if volatility > 0 else 0

    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_drawdown = drawdown.min()

    positive_count = (daily_returns > 0).sum()
    total_trading_days = len(daily_returns)
    win_rate = positive_count / total_trading_days if total_trading_days > 0 else 0

    cum_returns = (1 + daily_returns).cumprod()
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    return {
        "总收益率": float(total_return),
        "年化收益率": float(annual_return),
        "年化波动率": float(volatility),
        "夏普比率": float(sharpe),
        "最大回撤": float(max_drawdown),
        "卡玛比率": float(calmar),
        "胜率": float(win_rate),
        "交易天数": int(len(daily_returns)),
    }


def _safe(val, default=0):
    if val is None:
        return default
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return default
    return float(val)


def calculate_trade_metrics(trades: list) -> dict:
    if not trades:
        return {}

    profits = [t.get("pnl", 0) for t in trades if t.get("action") == "sell"]
    winning_trades = [p for p in profits if p > 0]
    losing_trades = [p for p in profits if p <= 0]

    win_rate = len(winning_trades) / len(profits) if profits else 0
    avg_win = float(np.mean(winning_trades)) if winning_trades else 0
    avg_loss = float(abs(np.mean(losing_trades))) if losing_trades else 0
    profit_factor = float(sum(winning_trades) / abs(sum(losing_trades))) if losing_trades and sum(losing_trades) != 0 else 0
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    return {
        "总交易次数": int(len(profits)),
        "盈利次数": int(len(winning_trades)),
        "亏损次数": int(len(losing_trades)),
        "胜率": float(win_rate),
        "平均盈利": _safe(avg_win),
        "平均亏损": _safe(avg_loss),
        "盈亏比": _safe(win_loss_ratio),
        "利润因子": _safe(profit_factor),
        "总盈利": _safe(sum(winning_trades)),
        "总亏损": _safe(abs(sum(losing_trades))),
        "净利润": _safe(sum(profits)),
    }


def format_metrics(metrics: dict) -> dict:
    fmt = {
        "总收益率": f"{metrics.get('总收益率', 0) * 100:.2f}%",
        "年化收益率": f"{metrics.get('年化收益率', 0) * 100:.2f}%",
        "年化波动率": f"{metrics.get('年化波动率', 0) * 100:.2f}%",
        "夏普比率": f"{metrics.get('夏普比率', 0):.2f}",
        "最大回撤": f"{metrics.get('最大回撤', 0) * 100:.2f}%",
        "卡玛比率": f"{metrics.get('卡玛比率', 0):.2f}",
        "胜率": f"{metrics.get('胜率', 0) * 100:.2f}%",
        "交易天数": str(metrics.get("交易天数", 0)),
    }
    return fmt
