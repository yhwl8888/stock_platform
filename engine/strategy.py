from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import pandas as pd
import numpy as np


@dataclass
class Signal:
    code: str
    date: str
    action: str  # "buy" or "sell"
    price: float
    reason: str = ""


class Strategy(ABC):
    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
        self.signals: List[Signal] = []
        self.data: dict[str, pd.DataFrame] = {}

    def set_data(self, data: dict[str, pd.DataFrame]):
        self.data = data

    def add_signal(self, code: str, date: str, action: str, price: float, reason: str = ""):
        self.signals.append(Signal(code, date, action, price, reason))

    @abstractmethod
    def on_data(self, code: str, df: pd.DataFrame):
        ...

    def clear_signals(self):
        self.signals.clear()

    def get_signals(self) -> List[Signal]:
        return self.signals


class MaCrossStrategy(Strategy):
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        if fast_period >= slow_period:
            slow_period = fast_period + 10
        super().__init__(f"MA{fast_period}_{slow_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.slow_period + 1:
            return
        close = df["close"].values
        ma_fast = np.convolve(close, np.ones(self.fast_period) / self.fast_period, mode="valid")
        ma_slow = np.convolve(close, np.ones(self.slow_period) / self.slow_period, mode="valid")
        align = self.slow_period - self.fast_period
        for i in range(1, len(ma_fast)):
            idx = i + self.slow_period - 1
            if idx >= len(df):
                break
            date = str(df.index[idx].date()) if hasattr(df.index[idx], "date") else str(df.index[idx])
            price = float(close[idx])
            prev_fast = ma_fast[i - 1]
            prev_slow = ma_slow[i - 1 - align] if align <= i - 1 else ma_fast[i - 1]
            if prev_fast <= prev_slow and ma_fast[i] > ma_slow[i - align]:
                self.add_signal(code, date, "buy", price, f"MA{self.fast_period}上穿MA{self.slow_period}")
            elif prev_fast >= prev_slow and ma_fast[i] < ma_slow[i - align]:
                self.add_signal(code, date, "sell", price, f"MA{self.fast_period}下穿MA{self.slow_period}")


class RsiStrategy(Strategy):
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__(f"RSI_{period}")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.period + 1:
            return
        close = df["close"].values
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.zeros(len(deltas))
        avg_loss = np.zeros(len(deltas))
        avg_gain[self.period - 1] = np.mean(gains[:self.period])
        avg_loss[self.period - 1] = np.mean(losses[:self.period])
        for i in range(self.period, len(deltas)):
            avg_gain[i] = (avg_gain[i - 1] * (self.period - 1) + gains[i]) / self.period
            avg_loss[i] = (avg_loss[i - 1] * (self.period - 1) + losses[i]) / self.period
        rs = np.divide(avg_gain, avg_loss, out=np.ones_like(avg_gain), where=avg_loss != 0)
        rsi = 100 - (100 / (1 + rs))
        in_position = False
        for i in range(self.period, len(deltas)):
            idx = i + 1
            if idx >= len(df):
                break
            date = str(df.index[idx].date()) if hasattr(df.index[idx], "date") else str(df.index[idx])
            price = float(close[idx])
            if not in_position and rsi[i] < self.oversold:
                self.add_signal(code, date, "buy", price, f"RSI触及超卖({rsi[i]:.1f})")
                in_position = True
            elif in_position and rsi[i] > self.overbought:
                self.add_signal(code, date, "sell", price, f"RSI触及超买({rsi[i]:.1f})")
                in_position = False


class BollingerStrategy(Strategy):
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(f"Boll_{period}")
        self.period = period
        self.std_dev = std_dev

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.period:
            return
        close = df["close"].values
        middle = np.convolve(close, np.ones(self.period) / self.period, mode="valid")
        upper = np.zeros_like(middle)
        lower = np.zeros_like(middle)
        for i in range(len(middle)):
            idx = i + self.period - 1
            window = close[idx - self.period + 1: idx + 1]
            std = np.std(window)
            upper[i] = middle[i] + self.std_dev * std
            lower[i] = middle[i] - self.std_dev * std
        for i in range(1, len(middle)):
            idx = i + self.period - 1
            if idx >= len(close):
                break
            date = str(df.index[idx].date()) if hasattr(df.index[idx], "date") else str(df.index[idx])
            price = float(close[idx])
            if close[idx - 1] > lower[i - 1] and close[idx] <= lower[i]:
                self.add_signal(code, date, "buy", price, "股价触及下轨")
            elif close[idx - 1] < upper[i - 1] and close[idx] >= upper[i]:
                self.add_signal(code, date, "sell", price, "股价触及上轨")


class MacdStrategy(Strategy):
    def __init__(self, fast: int = 12, slow: int = 26, signal_period: int = 9):
        super().__init__(f"MACD_{fast}_{slow}_{signal_period}")
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.slow + self.signal_period:
            return
        close = df["close"].values
        ema_fast = np.zeros(len(close))
        ema_slow = np.zeros(len(close))
        ema_fast[:self.fast] = np.mean(close[:self.fast])
        ema_slow[:self.slow] = np.mean(close[:self.slow])
        for i in range(self.fast, len(close)):
            ema_fast[i] = (close[i] - ema_fast[i - 1]) * (2 / (self.fast + 1)) + ema_fast[i - 1]
        for i in range(self.slow, len(close)):
            ema_slow[i] = (close[i] - ema_slow[i - 1]) * (2 / (self.slow + 1)) + ema_slow[i - 1]
        dif = ema_fast - ema_slow
        dea = np.zeros(len(dif))
        if len(dif) >= self.signal_period:
            dea[:self.signal_period] = np.mean(dif[:self.signal_period])
            for i in range(self.signal_period, len(dif)):
                dea[i] = (dif[i] - dea[i - 1]) * (2 / (self.signal_period + 1)) + dea[i - 1]
        macd_line = 2 * (dif - dea)
        in_position = False
        for i in range(1, len(macd_line)):
            if i >= len(df):
                break
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            if not in_position and macd_line[i - 1] < 0 and macd_line[i] >= 0:
                self.add_signal(code, date, "buy", price, "MACD 零轴下方金叉")
                in_position = True
            elif in_position and macd_line[i - 1] > 0 and macd_line[i] <= 0:
                self.add_signal(code, date, "sell", price, "MACD 零轴上方死叉")
                in_position = False


class EmaCrossStrategy(Strategy):
    def __init__(self, fast_period: int = 12, slow_period: int = 26):
        if fast_period >= slow_period:
            slow_period = fast_period + 10
        super().__init__(f"EMA{fast_period}_{slow_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.slow_period + 1:
            return
        close = df["close"].values
        ema_fast = np.zeros(len(close))
        ema_slow = np.zeros(len(close))
        ema_fast[:self.fast_period] = np.mean(close[:self.fast_period])
        ema_slow[:self.slow_period] = np.mean(close[:self.slow_period])
        for i in range(self.fast_period, len(close)):
            ema_fast[i] = (close[i] - ema_fast[i - 1]) * (2 / (self.fast_period + 1)) + ema_fast[i - 1]
        for i in range(self.slow_period, len(close)):
            ema_slow[i] = (close[i] - ema_slow[i - 1]) * (2 / (self.slow_period + 1)) + ema_slow[i - 1]
        in_position = False
        for i in range(self.slow_period + 1, len(close)):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            if not in_position and ema_fast[i - 1] <= ema_slow[i - 1] and ema_fast[i] > ema_slow[i]:
                self.add_signal(code, date, "buy", price, f"EMA{self.fast_period}上穿 EMA{self.slow_period}")
                in_position = True
            elif in_position and ema_fast[i - 1] >= ema_slow[i - 1] and ema_fast[i] < ema_slow[i]:
                self.add_signal(code, date, "sell", price, f"EMA{self.fast_period}下穿 EMA{self.slow_period}")
                in_position = False


strategy_registry = {
    "ma_cross": {"cls": MaCrossStrategy, "label": "均线金叉死叉"},
    "rsi": {"cls": RsiStrategy, "label": "RSI 超买超卖"},
    "bollinger": {"cls": BollingerStrategy, "label": "布林带"},
    "macd": {"cls": MacdStrategy, "label": "MACD 指标"},
    "ema_cross": {"cls": EmaCrossStrategy, "label": "EMA 指数均线"},
}

def create_strategy(name: str, **kwargs) -> Strategy:
    entry = strategy_registry.get(name)
    if entry is None:
        raise ValueError(f"未知策略: {name}")
    cls = entry["cls"]
    return cls(**kwargs)

def get_strategy_label(name: str) -> str:
    entry = strategy_registry.get(name)
    return entry["label"] if entry else name
