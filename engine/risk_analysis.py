from dataclasses import dataclass, field
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
from engine.metrics import calculate_metrics, _safe


@dataclass
class RiskReport:
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    sortino: float
    calmar: float
    ulcer_index: float
    skewness: float
    kurtosis: float
    win_rate: float
    beta: float
    info_ratio: float

def calculate_risk_metrics(equity_curve: pd.Series, benchmark: Optional[pd.Series] = None,
                           rf: float = 0.03) -> dict:
    if equity_curve.empty or len(equity_curve) < 2:
        return {}
    
    daily_returns = equity_curve.pct_change().dropna()
    if daily_returns.empty:
        return {}
    
    # Value at Risk
    var_95 = float(np.percentile(daily_returns, 5))
    var_99 = float(np.percentile(daily_returns, 1))
    
    # Conditional VaR
    cvar_95 = float(daily_returns[daily_returns <= var_95].mean()) if var_95 < 0 else 0
    cvar_99 = float(daily_returns[daily_returns <= var_99].mean()) if var_99 < 0 else 0
    
    # Sortino ratio
    downside_returns = daily_returns[daily_returns < 0]
    downside_std = float(downside_returns.std()) if len(downside_returns) > 0 else 0
    annual_return = (1 + daily_returns.mean()) ** 252 - 1
    sortino = (annual_return - rf) / (downside_std * np.sqrt(252)) if downside_std > 0 else 0
    
    # Calmar ratio
    max_drawdown = (equity_curve / equity_curve.cummax()).min()
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Ulcer Index
    drawdown_pct = (equity_curve - equity_curve.cummax()) / equity_curve.cummax() * 100
    ulcer_index = float(np.sqrt(np.mean(drawdown_pct ** 2)))
    
    # Skewness and Kurtosis
    skewness = float(daily_returns.skew())
    kurtosis = float(daily_returns.kurtosis())
    
    # Win rate
    win_rate = float((daily_returns > 0).mean())
    
    # Best/Worst consecutive
    positive_run = 1
    max_positive_run = 1
    negative_run = 1
    max_negative_run = 1
    for ret in daily_returns:
        if ret > 0:
            positive_run += 1
            max_positive_run = max(max_positive_run, positive_run)
        else:
            positive_run = 0
        if ret < 0:
            negative_run += 1
            max_negative_run = max(max_negative_run, negative_run)
        else:
            negative_run = 0
    
    # Beta vs benchmark
    beta = 0.0
    if benchmark is not None and not benchmark.empty:
        aligned = pd.DataFrame({
            "portfolio": daily_returns,
            "benchmark": benchmark.pct_change().dropna()
        }).dropna()
        if len(aligned) > 2:
            cov_matrix = aligned.cov()
            if cov_matrix.iloc[1, 1] > 0:
                beta = float(cov_matrix.iloc[0, 1] / cov_matrix.iloc[1, 1])
    
    # Information ratio
    tracking_error = 0.0
    if benchmark is not None and not benchmark.empty:
        aligned = pd.DataFrame({
            "portfolio": daily_returns,
            "benchmark": benchmark.pct_change().dropna()
        }).dropna()
        if len(aligned) > 2:
            active_return = aligned["portfolio"] - aligned["benchmark"]
            tracking_error = float(active_return.std() * np.sqrt(252))
        info_ratio = (annual_return) / tracking_error if tracking_error > 0 else 0
    else:
        info_ratio = 0
    
    return {
        "VaR_95": var_95,
        "VaR_99": var_99,
        "CVaR_95": cvar_95,
        "CVaR_99": cvar_99,
        "Sortino_姣旂巼": sortino,
        "Calmar_姣旂巼": calmar,
        "Ulcer_鎸囨暟": ulcer_index,
        "鍋忓害": skewness,
        "宄板害": kurtosis,
        "鑳滅巼": win_rate,
        "鏈€澶ц繛缁泩鍒": max_positive_run,
        "鏈€澶ц繛缁簭鎹": max_negative_run,
        "Beta": beta,
        "淇℃伅姣旂巼": info_ratio,
    }


def generate_risk_report(equity_curve: pd.Series, benchmark: Optional[pd.Series] = None,
                         rf: float = 0.03) -> dict:
    """生成完整风险报告，合并所有指标并附带格式化字符串。"""
    if equity_curve.empty or len(equity_curve) < 2:
        return {}

    metrics = calculate_risk_metrics(equity_curve, benchmark, rf)
    if not metrics:
        return {}

    daily_returns = equity_curve.pct_change().dropna()
    annual_return = (1 + daily_returns.mean()) ** 252 - 1
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)
    volatility = float(daily_returns.std() * np.sqrt(252))
    max_dd = float((equity_curve / equity_curve.cummax()).min())

    # 附加连续盈亏分析
    consec = calculate_max_consecutive(equity_curve)
    metrics.update(consec)

    # 格式化字符串
    formatted = {
        "总收益率": f"{total_return:.2%}",
        "年化收益率": f"{annual_return:.2%}",
        "年化波动率": f"{volatility:.2%}",
        "最大回撤": f"{max_dd:.2%}",
        "VaR(95%)": f"{metrics.get('VaR_95', 0):.4%}",
        "VaR(99%)": f"{metrics.get('VaR_99', 0):.4%}",
        "CVaR(95%)": f"{metrics.get('CVaR_95', 0):.4%}",
        "CVaR(99%)": f"{metrics.get('CVaR_99', 0):.4%}",
        "Sortino比率": f"{metrics.get('Sortino_姣旂巼', 0):.2f}",
        "Calmar比率": f"{metrics.get('Calmar_姣旂巼', 0):.2f}",
        "Ulcer指数": f"{metrics.get('Ulcer_鎸囨暟', 0):.2f}",
        "偏度": f"{metrics.get('鍋忓害', 0):.4f}",
        "峰度": f"{metrics.get('宄板害', 0):.4f}",
        "胜率": f"{metrics.get('鑳滅巼', 0):.2%}",
        "Beta": f"{metrics.get('Beta', 0):.4f}",
        "信息比率": f"{metrics.get('淇℃伅姣旂巼', 0):.4f}",
        "最大连续盈利天数": str(metrics.get("最大连续盈利", 0)),
        "最大连续亏损天数": str(metrics.get("最大连续亏损", 0)),
    }

    return {
        "raw_metrics": metrics,
        "formatted": formatted,
        "total_return": total_return,
        "annual_return": annual_return,
        "volatility": volatility,
        "max_drawdown": max_dd,
    }


def calculate_max_consecutive(equity_curve: pd.Series) -> dict:
    """计算最大连续盈利/亏损天数。"""
    if equity_curve.empty or len(equity_curve) < 2:
        return {"最大连续盈利": 0, "最大连续亏损": 0}

    daily_returns = equity_curve.pct_change().dropna()
    if daily_returns.empty:
        return {"最大连续盈利": 0, "最大连续亏损": 0}

    max_win = 0
    max_loss = 0
    curr_win = 0
    curr_loss = 0

    for ret in daily_returns:
        if ret > 0:
            curr_win += 1
            curr_loss = 0
            max_win = max(max_win, curr_win)
        elif ret < 0:
            curr_loss += 1
            curr_win = 0
            max_loss = max(max_loss, curr_loss)
        else:
            curr_win = 0
            curr_loss = 0

    return {"最大连续盈利": max_win, "最大连续亏损": max_loss}


def rolling_sharpe(equity_curve: pd.Series, window: int = 60, rf: float = 0.03) -> pd.Series:
    """计算滚动夏普比率。"""
    if equity_curve.empty or len(equity_curve) < window:
        return pd.Series(dtype=float)

    daily_returns = equity_curve.pct_change().dropna()
    if len(daily_returns) < window:
        return pd.Series(dtype=float)

    rolling_mean = daily_returns.rolling(window=window).mean()
    rolling_std = daily_returns.rolling(window=window).std()
    daily_rf = rf / 252

    sharpe = (rolling_mean - daily_rf) / rolling_std * np.sqrt(252)
    sharpe = sharpe.replace([np.inf, -np.inf], np.nan).dropna()
    return sharpe


def rolling_volatility(equity_curve: pd.Series, window: int = 60) -> pd.Series:
    """计算滚动年化波动率。"""
    if equity_curve.empty or len(equity_curve) < window:
        return pd.Series(dtype=float)

    daily_returns = equity_curve.pct_change().dropna()
    if len(daily_returns) < window:
        return pd.Series(dtype=float)

    vol = daily_returns.rolling(window=window).std() * np.sqrt(252)
    vol = vol.replace([np.inf, -np.inf], np.nan).dropna()
    return vol


def drawdown_analysis(equity_curve: pd.Series, top_n: int = 5) -> dict:
    """
    详细回撤分析：返回前 top_n 次最大回撤的起止日期、最大回撤值、回撤持续天数和恢复天数。
    """
    if equity_curve.empty or len(equity_curve) < 2:
        return {"drawdowns": [], "summary": {}}

    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax

    in_drawdown = drawdown < 0
    drawdowns = []

    if not in_drawdown.any():
        return {"drawdowns": [], "summary": {}}

    # 分割连续回撤区间
    groups = (~in_drawdown).cumsum()
    for _, group in drawdown.groupby(groups):
        negative = group[group < 0]
        if negative.empty:
            continue

        trough_idx = negative.idxmin()
        trough_val = float(negative.min())

        # 回撤开始：trough 之前最近的 peak
        pre_trough = equity_curve.loc[:trough_idx]
        peak_idx = pre_trough.idxmax()

        # 回撤结束：trough 之后恢复到 peak 的点
        peak_val = float(cummax.loc[peak_idx])
        post_trough = equity_curve.loc[trough_idx:]
        recovery_candidates = post_trough[post_trough >= peak_val]

        if len(recovery_candidates) > 0:
            recovery_idx = recovery_candidates.index[0]
            recovery_days = len(equity_curve.loc[trough_idx:recovery_idx]) - 1
        else:
            recovery_idx = None
            recovery_days = None  # 未恢复

        duration_days = len(equity_curve.loc[peak_idx:trough_idx]) - 1

        drawdowns.append({
            "peak_date": str(peak_idx),
            "trough_date": str(trough_idx),
            "recovery_date": str(recovery_idx) if recovery_idx is not None else None,
            "max_drawdown": trough_val,
            "duration_days": duration_days,
            "recovery_days": recovery_days,
        })

    # 按最大回撤排序取 top_n
    drawdowns.sort(key=lambda x: x["max_drawdown"])
    top_drawdowns = drawdowns[:top_n]

    # 汇总信息
    total_dd = len(drawdowns)
    unrecovered = sum(1 for d in drawdowns if d["recovery_days"] is None)
    avg_dd = float(np.mean([d["max_drawdown"] for d in drawdowns])) if drawdowns else 0
    max_dd = float(drawdown.min()) if not drawdown.empty else 0

    summary = {
        "total_drawdowns": total_dd,
        "unrecovered": unrecovered,
        "avg_drawdown": avg_dd,
        "max_drawdown": max_dd,
        "avg_duration_days": float(np.mean([d["duration_days"] for d in drawdowns])) if drawdowns else 0,
        "avg_recovery_days": float(np.mean([d["recovery_days"] for d in drawdowns if d["recovery_days"] is not None])) if any(d["recovery_days"] is not None for d in drawdowns) else None,
    }

    return {"drawdowns": top_drawdowns, "summary": summary}
