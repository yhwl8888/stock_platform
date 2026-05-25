from dataclasses import dataclass, field
from typing import List, Optional, Dict

import pandas as pd
import numpy as np

from config.settings import INITIAL_CAPITAL, TRADING_FEE_RATE, STAMP_TAX_RATE, MIN_TRADING_FEE


@dataclass
class PortfolioResult:
    portfolio_name: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    stock_performance: Dict[str, dict]
    trades: List[dict]
    metrics: dict


class PortfolioBacktest:
    def __init__(self, portfolio_name: str = "My Portfolio", initial_capital: float = INITIAL_CAPITAL):
        self.portfolio_name = portfolio_name
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict = {}
        self.trades: List[dict] = []
        self.equity_log: List[float] = []
        self.dates: List[str] = []
        
    def reset(self):
        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_log.clear()
        self.dates.clear()
        
    def _calc_fee(self, amount: float) -> float:
        return max(amount * TRADING_FEE_RATE, MIN_TRADING_FEE)
        
    def _calc_stamp_tax(self, amount: float) -> float:
        return amount * STAMP_TAX_RATE
        
    def add_position(self, code: str, shares: int, price: float):
        self.positions[code] = {
            "shares": shares,
            "cost": price,
            "entry_date": self.dates[-1] if self.dates else ""
        }
        
    def run(self,
           stock_data: dict,
           allocation_method: str = "equal_weight",
           custom_weights: dict = None,
           rebalance_frequency: str = "monthly",
           transaction_cost: float = 0.001) -> PortfolioResult:
        self.reset()
        
        stocks = list(stock_data.keys())
        if not stocks:
            return self._empty_result()
        
        if custom_weights:
            weights = {s: custom_weights.get(s, 1.0 / len(stocks)) for s in stocks}
        elif allocation_method == "equal_weight" or not allocation_method:
            weights = {s: 1.0 / len(stocks) for s in stocks}
        else:
            total = sum(custom_weights.values())
            weights = {s: w / total for s, w in custom_weights.items()}
        
        all_dates = set()
        for code, df in stock_data.items():
            for date in df.index:
                all_dates.add(str(date.date()) if hasattr(date, "date") else str(date))
        all_dates = sorted(all_dates)
        
        if rebalance_frequency == "daily":
            rebalance_check = lambda i: True
        elif rebalance_frequency == "weekly":
            rebalance_check = lambda i: i % 5 == 0
        else:
            prev_month = None
            def rebalance_check(i):
                nonlocal prev_month
                if not self.dates:
                    return False
                curr = pd.to_datetime(self.dates[-1])
                this_month = curr.month
                if prev_month is None:
                    prev_month = this_month
                    return False
                if this_month != prev_month:
                    prev_month = this_month
                    return True
                return False
        
        for i, date_str in enumerate(all_dates):
            self.dates.append(date_str)
            total_value = self.cash
            
            for code, pos_data in self.positions.items():
                if code in stock_data and len(stock_data[code]) > 0:
                    try:
                        dt = pd.to_datetime(date_str)
                        if dt in stock_data[code].index:
                            price = float(stock_data[code].loc[dt, "close"])
                        else:
                            dates_before = stock_data[code].index[stock_data[code].index <= dt]
                            if not dates_before.empty:
                                price = float(stock_data[code].loc[dates_before[-1], "close"])
                            else:
                                price = 0
                    except Exception:
                        if not stock_data[code].empty:
                            price = float(stock_data[code].iloc[-1]["close"])
                        else:
                            price = 0
                    
                    pos_value = pos_data["shares"] * price
                    total_value += pos_value
            
            self.equity_log.append(total_value)
            
            if rebalance_check(i):
                self._rebalance(stock_data, weights, transaction_cost)
            
            self._update_prices_and_check(stock_data, date_str)
        
        if not self.equity_log:
            return self._empty_result()
            
        equity_series = pd.Series(self.equity_log, index=pd.to_datetime(self.dates))
        cummax = equity_series.cummax()
        drawdown_series = (equity_series - cummax) / cummax
        
        stock_performance = {}
        for code, pos_data in self.positions.items():
            if code in stock_data and len(stock_data[code]) > 0:
                start_price = stock_data[code].iloc[0]["close"]
                end_price = stock_data[code].iloc[-1]["close"]
                stock_performance[code] = {
                    "cost_basis": pos_data["cost"],
                    "current_price": end_price,
                    "return": (end_price - pos_data["cost"]) / pos_data["cost"] * 100,
                    "shares": pos_data["shares"]
                }
        
        daily_returns = equity_series.pct_change().dropna()
        total_return = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1
        annual_return = (1 + total_return) ** (252 / len(daily_returns)) - 1
        volatility = daily_returns.std() * np.sqrt(252)
        sharpe = (annual_return - 0.03) / volatility if volatility > 0 else 0
        max_drawdown = drawdown_series.min()
        
        return PortfolioResult(
            portfolio_name=self.portfolio_name,
            initial_capital=self.initial_capital,
            final_capital=equity_series.iloc[-1],
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            volatility=volatility,
            equity_curve=equity_series,
            drawdown_curve=drawdown_series,
            stock_performance=stock_performance,
            trades=self.trades,
            metrics={
                "总收益率": float(total_return),
                "年化收益率": float(annual_return),
                "年化波动率": float(volatility),
                "夏普比率": float(sharpe),
                "最大回撤": float(max_drawdown),
            }
        )
        
    def _rebalance(self, stock_data: dict, weights: dict, transaction_cost: float):
        total_value = self.cash
        for code, pos_data in self.positions.items():
            if code in stock_data and len(stock_data[code]) > 0:
                try:
                    dt = pd.to_datetime(self.dates[-1])
                    if dt in stock_data[code].index:
                        price = float(stock_data[code].loc[dt, "close"])
                    else:
                        dates_before = stock_data[code].index[stock_data[code].index <= dt]
                        price = float(stock_data[code].loc[dates_before[-1], "close"]) if not dates_before.empty else 0
                except Exception:
                    price = float(stock_data[code].iloc[-1]["close"]) if not stock_data[code].empty else 0
                total_value += pos_data["shares"] * price
        
        target_value_each = total_value / len(weights)
        for code, weight in weights.items():
            target_value = total_value * weight
            pos = self.positions.get(code)
            if pos and pos["shares"] > 0:
                try:
                    dt = pd.to_datetime(self.dates[-1])
                    if dt in stock_data.get(code, pd.DataFrame()):
                        price = float(stock_data[code].loc[dt, "close"])
                    else:
                        dates_before = stock_data[code].index[stock_data[code].index <= dt]
                        price = float(stock_data[code].loc[dates_before[-1], "close"]) if not dates_before.empty else 0
                except Exception:
                    price = float(stock_data[code].iloc[-1]["close"]) if stock_data.get(code) and not stock_data[code].empty else 0
                
                current_value = pos["shares"] * price
                diff_value = target_value - current_value
                
                if abs(diff_value) > target_value * 0.05:
                    if diff_value > 0:
                        shares = min(int(diff_value / price / (1 + transaction_cost)) * 100, 1000000)
                        if shares > 0:
                            cost = shares * price * (1 + transaction_cost)
                            if cost <= self.cash:
                                self.cash -= cost
                                pos["shares"] += shares
                                pos["cost"] = (pos["cost_total"] + cost) / pos["shares"]
                    else:
                        shares_to_sell = min(int(abs(diff_value) / price), pos["shares"])
                        if shares_to_sell > 0:
                            proceeds = shares_to_sell * price * (1 - transaction_cost)
                            if code in self.positions:
                                self.positions[code]["shares"] -= shares_to_sell
                                if self.positions[code]["shares"] == 0:
                                    del self.positions[code]
    
    def _update_prices_and_check(self, stock_data: dict, date_str: str):
        pass
        
    def _empty_result(self) -> PortfolioResult:
        return PortfolioResult(
            portfolio_name=self.portfolio_name,
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0,
            annual_return=0,
            sharpe_ratio=0,
            max_drawdown=0,
            volatility=0,
            equity_curve=pd.Series(dtype=float),
            drawdown_curve=pd.Series(dtype=float),
            stock_performance={},
            trades=[],
            metrics={}
        )


def create_portfolio_backtest(portfolio_name: str = "My Portfolio",
                              initial_capital: float = INITIAL_CAPITAL) -> PortfolioBacktest:
    return PortfolioBacktest(portfolio_name, initial_capital)
