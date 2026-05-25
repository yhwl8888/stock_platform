from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd
import numpy as np

from engine.strategy import Strategy, Signal
from engine.metrics import calculate_metrics, calculate_trade_metrics
from config.settings import INITIAL_CAPITAL, TRADING_FEE_RATE, STAMP_TAX_RATE, MIN_TRADING_FEE


@dataclass
class Order:
    code: str
    date: str
    action: str
    price: float
    shares: float
    amount: float
    fee: float = 0
    status: str = "filled"


@dataclass
class Position:
    code: str
    shares: float = 0
    cost: float = 0
    current_price: float = 0


@dataclass
class BacktestResult:
    code: str
    strategy_name: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    trades: List[dict]
    signals: List[Signal]
    metrics: dict
    trade_metrics: dict


class BacktestEngine:
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[dict] = []
        self.equity_curve: List[float] = []
        self.dates: List[str] = []
        self.cash: float = initial_capital

    def reset(self):
        self.capital = self.initial_capital
        self.positions.clear()
        self.orders.clear()
        self.trades.clear()
        self.equity_curve.clear()
        self.dates.clear()
        self.cash = self.initial_capital

    def _calc_fee(self, amount: float) -> float:
        return max(amount * TRADING_FEE_RATE, MIN_TRADING_FEE)

    def _calc_stamp_tax(self, amount: float) -> float:
        return amount * STAMP_TAX_RATE

    def run(self, strategy: Strategy, data: dict[str, pd.DataFrame]) -> BacktestResult:
        self.reset()
        strategy.clear_signals()
        strategy.set_data(data)

        for code, df in data.items():
            if df.empty or len(df) < 20:
                continue
            strategy.on_data(code, df)

        signals = strategy.get_signals()
        signals.sort(key=lambda s: s.date)

        combined = self._build_combined_data(data)
        if combined.empty:
            return self._make_empty_result(strategy)

        equity_log = []

        for date, row in combined.iterrows():
            date_str = str(date.date()) if hasattr(date, "date") else str(date)
            day_signals = [s for s in signals if s.date == date_str]

            for sig in day_signals:
                if sig.code not in data or data[sig.code].empty:
                    continue
                price = sig.price
                if sig.action == "buy":
                    pos = self.positions.get(sig.code)
                    if pos and pos.shares > 0:
                        continue
                    shares = int(self.cash * 0.95 / (price * 100)) * 100
                    if shares < 100:
                        continue
                    amount = shares * price
                    fee = self._calc_fee(amount)
                    total_cost = amount + fee
                    if total_cost > self.cash:
                        continue
                    self.cash -= total_cost
                    self.positions[sig.code] = Position(
                        code=sig.code, shares=shares, cost=price
                    )
                    self.orders.append(Order(
                        code=sig.code, date=date_str, action="buy",
                        price=price, shares=shares, amount=amount, fee=fee
                    ))
                elif sig.action == "sell":
                    pos = self.positions.get(sig.code)
                    if pos is None or pos.shares == 0:
                        continue
                    amount = pos.shares * price
                    fee = self._calc_fee(amount)
                    tax = self._calc_stamp_tax(amount)
                    net = amount - fee - tax
                    pnl = net - (pos.shares * pos.cost + self._calc_fee(pos.shares * pos.cost))
                    self.cash += net
                    self.trades.append({
                        "code": sig.code, "buy_date": "", "sell_date": date_str,
                        "buy_price": pos.cost, "sell_price": price,
                        "shares": pos.shares, "pnl": pnl, "action": "sell",
                        "reason": sig.reason
                    })
                    self.orders.append(Order(
                        code=sig.code, date=date_str, action="sell",
                        price=price, shares=pos.shares, amount=amount, fee=fee
                    ))
                    del self.positions[sig.code]

            pos_value = sum(
                pos.shares * self._get_price(data, pos.code, date_str)
                for pos in self.positions.values()
            )
            total_equity = self.cash + pos_value
            equity_log.append(total_equity)
            self.dates.append(date_str)

        if not equity_log:
            return self._make_empty_result(strategy)

        equity_series = pd.Series(equity_log, index=pd.to_datetime(self.dates))
        cummax = equity_series.cummax()
        drawdown_series = (equity_series - cummax) / cummax

        metrics = calculate_metrics(equity_series)
        trade_metrics = calculate_trade_metrics(self.trades)

        return BacktestResult(
            code="multi",
            strategy_name=strategy.name,
            initial_capital=self.initial_capital,
            final_capital=equity_log[-1],
            total_return=metrics.get("总收益率", 0),
            annual_return=metrics.get("年化收益率", 0),
            sharpe=metrics.get("夏普比率", 0),
            max_drawdown=metrics.get("最大回撤", 0),
            win_rate=metrics.get("胜率", 0),
            total_trades=len(self.trades),
            equity_curve=equity_series,
            drawdown_curve=drawdown_series,
            trades=self.trades,
            signals=signals,
            metrics=metrics,
            trade_metrics=trade_metrics,
        )

    def _build_combined_data(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
        frames = []
        for code, df in data.items():
            if df.empty:
                continue
            s = df["close"].copy()
            s.name = code
            frames.append(s)
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, axis=1)
        combined["avg"] = combined.mean(axis=1)
        return combined

    def _get_price(self, data: dict, code: str, date_str: str) -> float:
        df = data.get(code)
        if df is None or df.empty:
            return 0
        try:
            dt = pd.to_datetime(date_str)
            if dt in df.index:
                return float(df.loc[dt, "close"])
            dates_before = df.index[df.index <= dt]
            if not dates_before.empty:
                return float(df.loc[dates_before[-1], "close"])
        except Exception:
            pass
        return float(df.iloc[-1]["close"]) if not df.empty else 0

    def _make_empty_result(self, strategy: Strategy) -> BacktestResult:
        return BacktestResult(
            code="", strategy_name=strategy.name,
            initial_capital=self.initial_capital, final_capital=self.initial_capital,
            total_return=0, annual_return=0, sharpe=0, max_drawdown=0,
            win_rate=0, total_trades=0,
            equity_curve=pd.Series(dtype=float),
            drawdown_curve=pd.Series(dtype=float),
            trades=[], signals=[],
            metrics={}, trade_metrics={}
        )


def run_backtest(strategy: Strategy, data: dict[str, pd.DataFrame],
                 initial_capital: float = INITIAL_CAPITAL) -> BacktestResult:
    engine = BacktestEngine(initial_capital)
    return engine.run(strategy, data)
