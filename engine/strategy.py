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


class KdjStrategy(Strategy):
    def __init__(self, period: int = 9):
        super().__init__(f"KDJ_{period}")
        self.period = period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.period + 2:
            return
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        n = len(close)
        rsv = np.zeros(n)
        k = np.full(n, 50.0)
        d = np.full(n, 50.0)
        for i in range(self.period - 1, n):
            hh = np.max(high[i - self.period + 1: i + 1])
            ll = np.min(low[i - self.period + 1: i + 1])
            denom = hh - ll
            rsv[i] = (close[i] - ll) / denom * 100 if denom != 0 else 50.0
            k[i] = 2 / 3 * k[i - 1] + 1 / 3 * rsv[i]
            d[i] = 2 / 3 * d[i - 1] + 1 / 3 * k[i]
        for i in range(self.period, n):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            if k[i - 1] <= d[i - 1] and k[i] > d[i] and k[i] < 20:
                self.add_signal(code, date, "buy", price, f"KDJ超卖金叉(K={k[i]:.1f},D={d[i]:.1f})")
            elif k[i - 1] >= d[i - 1] and k[i] < d[i] and k[i] > 80:
                self.add_signal(code, date, "sell", price, f"KDJ超买死叉(K={k[i]:.1f},D={d[i]:.1f})")


class AtrBreakoutStrategy(Strategy):
    def __init__(self, period: int = 14, multiplier: float = 2.0):
        super().__init__(f"ATR_{period}_{multiplier}")
        self.period = period
        self.multiplier = multiplier

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.period + 2:
            return
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        n = len(close)
        tr = np.zeros(n)
        tr[0] = high[0] - low[0]
        for i in range(1, n):
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        atr = np.zeros(n)
        atr[self.period - 1] = np.mean(tr[:self.period])
        for i in range(self.period, n):
            atr[i] = (atr[i - 1] * (self.period - 1) + tr[i]) / self.period
        sma = np.zeros(n)
        sma[:self.period - 1] = close[:self.period - 1]
        for i in range(self.period - 1, n):
            sma[i] = np.mean(close[i - self.period + 1: i + 1])
        upper = sma + self.multiplier * atr
        lower = sma - self.multiplier * atr
        for i in range(self.period, n):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            if close[i - 1] <= upper[i - 1] and close[i] > upper[i]:
                self.add_signal(code, date, "buy", price, f"ATR突破上轨({upper[i]:.2f})")
            elif close[i - 1] >= lower[i - 1] and close[i] < lower[i]:
                self.add_signal(code, date, "sell", price, f"ATR突破下轨({lower[i]:.2f})")


class DualMaStrategy(Strategy):
    def __init__(self, short_period: int = 5, medium_period: int = 20, long_period: int = 60):
        super().__init__(f"DualMA_{short_period}_{medium_period}_{long_period}")
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.long_period + 1:
            return
        close = df["close"].values
        n = len(close)
        ma_short = np.zeros(n)
        ma_medium = np.zeros(n)
        ma_long = np.zeros(n)
        for i in range(self.short_period - 1, n):
            ma_short[i] = np.mean(close[i - self.short_period + 1: i + 1])
        for i in range(self.medium_period - 1, n):
            ma_medium[i] = np.mean(close[i - self.medium_period + 1: i + 1])
        for i in range(self.long_period - 1, n):
            ma_long[i] = np.mean(close[i - self.long_period + 1: i + 1])
        in_position = False
        for i in range(self.long_period, n):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            bull = ma_short[i] > ma_medium[i] > ma_long[i]
            bear = ma_short[i] < ma_medium[i] < ma_long[i]
            if not in_position and bull:
                self.add_signal(code, date, "buy", price, "三均线多头排列")
                in_position = True
            elif in_position and bear:
                self.add_signal(code, date, "sell", price, "三均线空头排列")
                in_position = False


class VwapStrategy(Strategy):
    def __init__(self, volume_factor: float = 1.5):
        super().__init__(f"VWAP_{volume_factor}")
        self.volume_factor = volume_factor

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < 21:
            return
        close = df["close"].values
        volume = df["volume"].values.astype(float)
        typical_price = (df["high"].values + df["low"].values + close) / 3
        n = len(close)
        vwap = np.zeros(n)
        cum_tp_vol = 0.0
        cum_vol = 0.0
        for i in range(n):
            cum_tp_vol += typical_price[i] * volume[i]
            cum_vol += volume[i]
            vwap[i] = cum_tp_vol / cum_vol if cum_vol != 0 else 0
        avg_vol = np.zeros(n)
        for i in range(19, n):
            avg_vol[i] = np.mean(volume[i - 19: i + 1])
        for i in range(20, n):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            vol_surge = volume[i] > self.volume_factor * avg_vol[i]
            if close[i - 1] <= vwap[i - 1] and close[i] > vwap[i] and vol_surge:
                self.add_signal(code, date, "buy", price, f"VWAP量价突破(量比={volume[i]/avg_vol[i]:.2f})")
            elif close[i - 1] >= vwap[i - 1] and close[i] < vwap[i]:
                self.add_signal(code, date, "sell", price, "VWAP下跌突破")


class ObvStrategy(Strategy):
    def __init__(self, period: int = 20):
        super().__init__(f"OBV_{period}")
        self.period = period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.period + 1:
            return
        close = df["close"].values
        volume = df["volume"].values.astype(float)
        direction = np.sign(np.diff(close, prepend=close[0]))
        obv = np.cumsum(direction * volume)
        for i in range(self.period, len(close)):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            obv_change = obv[i] - obv[i - self.period]
            price_change = close[i] - close[i - self.period]
            if obv_change > 0 and price_change <= 0:
                self.add_signal(code, date, "buy", price, "OBV量能背离(量升价跌)")
            elif obv_change < 0 and price_change >= 0:
                self.add_signal(code, date, "sell", price, "OBV量能背离(量降价升)")


class TripleEmaStrategy(Strategy):
    def __init__(self, short_period: int = 5, medium_period: int = 10, long_period: int = 20):
        super().__init__(f"TripleEMA_{short_period}_{medium_period}_{long_period}")
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.long_period + 1:
            return
        close = df["close"].values
        n = len(close)
        ema_s = np.zeros(n)
        ema_m = np.zeros(n)
        ema_l = np.zeros(n)
        ema_s[:self.short_period] = np.mean(close[:self.short_period])
        ema_m[:self.medium_period] = np.mean(close[:self.medium_period])
        ema_l[:self.long_period] = np.mean(close[:self.long_period])
        for i in range(self.short_period, n):
            ema_s[i] = (close[i] - ema_s[i - 1]) * (2 / (self.short_period + 1)) + ema_s[i - 1]
        for i in range(self.medium_period, n):
            ema_m[i] = (close[i] - ema_m[i - 1]) * (2 / (self.medium_period + 1)) + ema_m[i - 1]
        for i in range(self.long_period, n):
            ema_l[i] = (close[i] - ema_l[i - 1]) * (2 / (self.long_period + 1)) + ema_l[i - 1]
        in_position = False
        for i in range(self.long_period + 1, n):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            bull_now = ema_s[i] > ema_m[i] > ema_l[i]
            bull_prev = ema_s[i - 1] > ema_m[i - 1] > ema_l[i - 1]
            bear_now = ema_s[i] < ema_m[i] < ema_l[i]
            if not in_position and bull_now and not bull_prev:
                self.add_signal(code, date, "buy", price, "三EMA开始多头排列")
                in_position = True
            elif in_position and bear_now:
                self.add_signal(code, date, "sell", price, "三EMA空头排列")
                in_position = False


class IchimokuStrategy(Strategy):
    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_period: int = 52):
        super().__init__(f"Ichimoku_{tenkan_period}_{kijun_period}_{senkou_period}")
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_period = senkou_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < self.senkou_period:
            return
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        n = len(close)
        tenkan = np.zeros(n)
        kijun = np.zeros(n)
        for i in range(self.tenkan_period - 1, n):
            hh = np.max(high[i - self.tenkan_period + 1: i + 1])
            ll = np.min(low[i - self.tenkan_period + 1: i + 1])
            tenkan[i] = (hh + ll) / 2
        for i in range(self.kijun_period - 1, n):
            hh = np.max(high[i - self.kijun_period + 1: i + 1])
            ll = np.min(low[i - self.kijun_period + 1: i + 1])
            kijun[i] = (hh + ll) / 2
        senkou_a = np.zeros(n)
        for i in range(self.kijun_period - 1, n):
            senkou_a[i] = (tenkan[i] + kijun[i]) / 2
        senkou_b = np.zeros(n)
        for i in range(self.senkou_period - 1, n):
            hh = np.max(high[i - self.senkou_period + 1: i + 1])
            ll = np.min(low[i - self.senkou_period + 1: i + 1])
            senkou_b[i] = (hh + ll) / 2
        for i in range(self.senkou_period, n):
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            cloud_top = max(senkou_a[i], senkou_b[i])
            cloud_bot = min(senkou_a[i], senkou_b[i])
            above_cloud = tenkan[i] > kijun[i] and price > cloud_top
            below_cloud = tenkan[i] < kijun[i] and price < cloud_bot
            if above_cloud:
                self.add_signal(code, date, "buy", price, "一目均衡云图买入")
            elif below_cloud:
                self.add_signal(code, date, "sell", price, "一目均衡云图卖出")


class MeanReversionStrategy(Strategy):
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, rsi_period: int = 14):
        super().__init__(f"MeanRev_{bb_period}_{bb_std}_{rsi_period}")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period

    def on_data(self, code: str, df: pd.DataFrame):
        if len(df) < max(self.bb_period, self.rsi_period) + 1:
            return
        close = df["close"].values
        n = len(close)
        middle = np.zeros(n)
        upper = np.zeros(n)
        lower = np.zeros(n)
        for i in range(self.bb_period - 1, n):
            window = close[i - self.bb_period + 1: i + 1]
            middle[i] = np.mean(window)
            std = np.std(window)
            upper[i] = middle[i] + self.bb_std * std
            lower[i] = middle[i] - self.bb_std * std
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.zeros(len(deltas))
        avg_loss = np.zeros(len(deltas))
        avg_gain[self.rsi_period - 1] = np.mean(gains[:self.rsi_period])
        avg_loss[self.rsi_period - 1] = np.mean(losses[:self.rsi_period])
        for i in range(self.rsi_period, len(deltas)):
            avg_gain[i] = (avg_gain[i - 1] * (self.rsi_period - 1) + gains[i]) / self.rsi_period
            avg_loss[i] = (avg_loss[i - 1] * (self.rsi_period - 1) + losses[i]) / self.rsi_period
        rs = np.divide(avg_gain, avg_loss, out=np.ones_like(avg_gain), where=avg_loss != 0)
        rsi = 100 - (100 / (1 + rs))
        in_position = False
        for i in range(max(self.bb_period, self.rsi_period), n):
            rsi_idx = i - 1
            if rsi_idx >= len(rsi):
                break
            date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            price = float(close[i])
            if not in_position and close[i] <= lower[i] and rsi[rsi_idx] < 30:
                self.add_signal(code, date, "buy", price, f"均值回归(RSI={rsi[rsi_idx]:.1f}触碰下轨)")
                in_position = True
            elif in_position and close[i] >= upper[i] and rsi[rsi_idx] > 70:
                self.add_signal(code, date, "sell", price, f"均值回归(RSI={rsi[rsi_idx]:.1f}触碰上轨)")
                in_position = False


strategy_registry = {
    "ma_cross": {"cls": MaCrossStrategy, "label": "均线金叉死叉"},
    "rsi": {"cls": RsiStrategy, "label": "RSI 超买超卖"},
    "bollinger": {"cls": BollingerStrategy, "label": "布林带"},
    "macd": {"cls": MacdStrategy, "label": "MACD 指标"},
    "ema_cross": {"cls": EmaCrossStrategy, "label": "EMA 指数均线"},
    "kdj": {"cls": KdjStrategy, "label": "KDJ随机指标金叉死叉"},
    "atr_breakout": {"cls": AtrBreakoutStrategy, "label": "ATR通道突破"},
    "dual_ma": {"cls": DualMaStrategy, "label": "三均线多头排列"},
    "vwap": {"cls": VwapStrategy, "label": "VWAP量价突破"},
    "obv": {"cls": ObvStrategy, "label": "OBV量能背离"},
    "triple_ema": {"cls": TripleEmaStrategy, "label": "三重EMA趋势"},
    "ichimoku": {"cls": IchimokuStrategy, "label": "一目均衡云图"},
    "mean_reversion": {"cls": MeanReversionStrategy, "label": "均值回归"},
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
