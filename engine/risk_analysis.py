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
        "Sortino_比率": sortino,
        "Calmar_比率": calmar,
        "Ulcer_指数": ulcer_index,
        "偏度": skewness,
        "峰度": kurtosis,
        "胜率": win_rate,
        "最大连续盈利": max_positive_run,
        "最大连续亏损": max_negative_run,
        "Beta": beta,
        "信息比率": info_ratio,
    }
