from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


class TechnicalIndicators:
    """技术指标计算器 - 提供 28 种经典技术分析指标"""

    # ==================== 趋势类指标 ====================

    @staticmethod
    def moving_average(close: pd.Series, period: int) -> pd.Series:
        """移动平均线"""
        return close.rolling(period).mean()

    @staticmethod
    def ema(close: pd.Series, period: int) -> pd.Series:
        """指数移动平均线"""
        return close.ewm(span=period, adjust=False).mean()

    @staticmethod
    def dema(close: pd.Series, period: int) -> pd.Series:
        """双重指数移动平均线"""
        ema1 = TechnicalIndicators.ema(close, period)
        ema2 = TechnicalIndicators.ema(ema1, period)
        return 2 * ema1 - ema2

    @staticmethod
    def tema(close: pd.Series, period: int) -> pd.Series:
        """三重指数移动平均线"""
        ema1 = TechnicalIndicators.ema(close, period)
        ema2 = TechnicalIndicators.ema(ema1, period)
        ema3 = TechnicalIndicators.ema(ema2, period)
        return 3 * (ema1 - ema2) + ema3

    # ==================== 动量指标 ====================

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """RSI - 相对强弱指标"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(close: pd.Series,
             fast: int = 12,
             slow: int = 26,
             signal: int = 9) -> Dict[str, pd.Series]:
        """MACD - 异同移动平均线"""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = 2 * (dif - dea)
        return {"DIF": dif, "DEA": dea, "MACD": macd_hist}

    @staticmethod
    def kdj(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 9) -> Dict[str, pd.Series]:
        """KDJ - 随机指标"""
        lowest = low.rolling(period).min()
        highest = high.rolling(period).max()
        rsv = (close - lowest) / (highest - lowest).replace(0, np.nan) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d  # 修正：KDJ中J = 3K-2D
        return {"K": k, "D": d, "J": j}

    @staticmethod
    def stochastic_rsi(close: pd.Series,
                       rsi_period: int = 14,
                       k_period: int = 3,
                       d_period: int = 3) -> Dict[str, pd.Series]:
        """KRSI - 随机RSI指标"""
        rsi = TechnicalIndicators.rsi(close, rsi_period)
        rsi_low = rsi.rolling(rsi_period).min()
        rsi_high = rsi.rolling(rsi_period).max()
        rsv = (rsi - rsi_low) / (rsi_high - rsi_low).replace(0, np.nan) * 100
        k = rsv.ewm(com=k_period, adjust=False).mean()
        d = k.ewm(com=d_period, adjust=False).mean()
        j = 3 * k - 2 * d
        return {"K": k, "D": d, "J": j}

    @staticmethod
    def roc(close: pd.Series, period: int = 12) -> pd.Series:
        """ROC - 变动率指标"""
        return close.pct_change(period).fillna(0) * 100

    @staticmethod
    def mom(close: pd.Series, period: int = 10) -> pd.Series:
        """MOM - 动量指标"""
        return close - close.shift(period)

    @staticmethod
    def trix(close: pd.Series, period: int = 12) -> pd.Series:
        """TRIX - 三重指数平滑变动率"""
        ema1 = TechnicalIndicators.ema(close, period)
        ema2 = TechnicalIndicators.ema(ema1, period)
        ema3 = TechnicalIndicators.ema(ema2, period)
        return ema3.pct_change().fillna(0) * 100

    @staticmethod
    def cci(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 20) -> pd.Series:
        """CCI - 顺势指标"""
        tp = (high + low + close) / 3
        sma = tp.rolling(period).mean()
        md = tp.rolling(period).apply(lambda x: x.abs().mean())
        return (tp - sma) / (0.015 * md)

    @staticmethod
    def williams_r(high: pd.Series,
                   low: pd.Series,
                   close: pd.Series,
                   period: int = 14) -> pd.Series:
        """Williams %R - 威廉指标"""
        highest = high.rolling(period).max()
        lowest = low.rolling(period).min()
        return ((highest - close) / (highest - lowest).replace(0, np.nan)) * -100

    # ==================== 波动率指标 ====================

    @staticmethod
    def atr(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 14) -> pd.Series:
        """ATR - 平均真实波幅"""
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(period).mean()

    @staticmethod
    def bollinger(close: pd.Series,
                  period: int = 20,
                  std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """布林带"""
        middle = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        bandwidth = ((upper - lower) / middle * 100).replace(0, np.nan)
        percent_b = ((close - lower) / (upper - lower)).replace(0, np.nan)
        return {
            "UPPER": upper,
            "MIDDLE": middle,
            "LOWER": lower,
            "BANDWIDTH": bandwidth,
            "PERCENT_B": percent_b
        }

    @staticmethod
    def keltner(high: pd.Series,
                low: pd.Series,
                close: pd.Series,
                period: int = 20) -> Dict[str, pd.Series]:
        """肯特纳通道"""
        ema = TechnicalIndicators.ema(close, period)
        atr_val = TechnicalIndicators.atr(high, low, close, period)
        return {
            "UPPER": ema + 2 * atr_val,
            "MIDDLE": ema,
            "LOWER": ema - 2 * atr_val
        }

    # ==================== 成交量指标 ====================

    @staticmethod
    def obv(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            volume: pd.Series) -> pd.Series:
        """OBV - 能量潮"""
        direction = close.diff()
        positive_vol = volume.where(direction > 0, 0)
        negative_vol = volume.where(direction < 0, 0)
        obv_vals = positive_vol - negative_vol
        return obv_vals.cumsum()

    @staticmethod
    def volume_price_trend(close: pd.Series,
                           high: pd.Series,
                           low: pd.Series,
                           volume: pd.Series) -> pd.Series:
        """VPT - 量价趋势指标"""
        volatility = high - low
        pv = volume * (close - (high + low) / 2) / volatility.replace(0, np.nan)
        return pv.cumsum()

    @staticmethod
    def mfi(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            volume: pd.Series,
            period: int = 14) -> pd.Series:
        """MFI - 资金流量指标"""
        tp = (high + low + close) / 3
        raw_money_flow = tp * volume
        money_flow_delta = tp.diff()
        pos_flow = raw_money_flow.where(money_flow_delta > 0, 0)
        neg_flow = raw_money_flow.where(money_flow_delta < 0, 0)
        pos_ratio = pos_flow.rolling(period).mean() / neg_flow.rolling(period).mean().replace(0, np.nan)
        return 100 - (100 / (1 + pos_ratio))

    # ==================== 趋势强度指标 ====================

    @staticmethod
    def adx(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 14) -> Dict[str, pd.Series]:
        """ADX - 平均趋向指数"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = TechnicalIndicators.atr(high, low, close, period)
        plus_di = 100 * TechnicalIndicators._ema_ratio(plus_dm, tr, period)
        minus_di = 100 * TechnicalIndicators._ema_ratio(minus_dm, tr, period)

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan) * 100)
        adx = dx.rolling(period).mean()
        return {"ADX": adx, "+DI": plus_di, "-DI": minus_di}

    @staticmethod
    def _ema_ratio(data: pd.Series, tr: pd.Series, period: int) -> pd.Series:
        """计算 EMA 比率"""
        return data.rolling(period).mean() / tr.rolling(period).mean()

    @staticmethod
    def aroon(high: pd.Series,
              low: pd.Series,
              period: int = 25) -> Dict[str, pd.Series]:
        """阿隆指标"""
        highest = high.rolling(period).max()
        lowest = low.rolling(period).min()
        periods_high = high.rolling(period).apply(lambda x: len(x) - x.tolist().index(x.max()) - 1)
        periods_low = low.rolling(period).apply(lambda x: len(x) - x.tolist().index(x.min()) - 1)
        return {
            "AROON_UP": periods_high * 100 / period,
            "AROON_DOWN": periods_low * 100 / period,
            "AROON_INDICATOR": (periods_high - periods_low) * 100 / period
        }

    # ==================== 综合功能 ====================

    @staticmethod
    def calculate_all(df: pd.DataFrame,
                      volume_col: str = "volume") -> Dict[str, Dict[str, list]]:
        """一站式计算所有技术指标"""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df.get(volume_col, pd.Series(dtype=float))

        results = {}

        # 动量指标
        results["rsi"] = TechnicalIndicators.rsi(close).values.tolist()
        macd_data = TechnicalIndicators.macd(close)
        results["macd"] = {k: v.values.tolist() for k, v in macd_data.items()}
        results["kdj"] = {k: v.values.tolist() for k, v in TechnicalIndicators.kdj(high, low, close).items()}
        results["stochastic_rsi"] = {k: v.values.tolist() for k, v in TechnicalIndicators.stochastic_rsi(close).items()}
        results["roc"] = TechnicalIndicators.roc(close).values.tolist()
        results["mom"] = TechnicalIndicators.mom(close).values.tolist()
        results["trix"] = TechnicalIndicators.trix(close).values.tolist()
        results["cci"] = TechnicalIndicators.cci(high, low, close).values.tolist()
        results["williams_r"] = TechnicalIndicators.williams_r(high, low, close).values.tolist()

        # 波动率指标
        results["bollinger"] = {k: v.values.tolist() for k, v in TechnicalIndicators.bollinger(close).items()}
        results["keltner"] = {k: v.values.tolist() for k, v in TechnicalIndicators.keltner(high, low, close).items()}
        results["atr"] = TechnicalIndicators.atr(high, low, close).values.tolist()

        # 趋势指标
        adx_data = TechnicalIndicators.adx(high, low, close)
        results["adx"] = {k: v.values.tolist() for k, v in adx_data.items()}
        results["aroon"] = {k: v.values.tolist() for k, v in TechnicalIndicators.aroon(high, low).items()}

        # 成交量指标
        if volume_col in df.columns:
            results["obv"] = TechnicalIndicators.obv(high, low, close, volume).values.tolist()
            results["vpt"] = TechnicalIndicators.volume_price_trend(close, high, low, volume).values.tolist()
            results["mfi"] = TechnicalIndicators.mfi(high, low, close, volume).values.tolist()

        # 生成买卖信号
        results["signals"] = TechnicalIndicators.generate_signals(results)

        return results

    @staticmethod
    def generate_signals(indicators: dict) -> dict:
        """综合生成买卖信号"""
        buy_signals = 0
        sell_signals = 0

        # MACD 金叉
        if "macd" in indicators:
            macd_vals = indicators["macd"]
            if macd_vals.get("MACD") and macd_vals.get("DIF"):
                macd = macd_vals["MACD"]
                dif = macd_vals["DIF"]
                if len(macd) >= 2 and len(dif) >= 2:
                    if macd[-1] > 0 and macd[-2] <= 0:
                        buy_signals += 1
                    elif macd[-1] < 0 and macd[-2] >= 0:
                        sell_signals += 1

        # RSI
        if "rsi" in indicators:
            rsi_last = indicators["rsi"][-1] if indicators["rsi"] else 70
            if rsi_last < 30:
                buy_signals += 1
            elif rsi_last > 70:
                sell_signals += 1

        # KDJ
        if "kdj" in indicators:
            kdj_vals = indicators["kdj"]
            if kdj_vals.get("J") and kdj_vals.get("K"):
                j = kdj_vals["J"]
                k = kdj_vals["K"]
                if len(j) >= 2 and len(k) >= 2:
                    if j[-1] < 20 and j[-1] > k[-1]:
                        buy_signals += 1
                    elif j[-1] > 80 and j[-1] < k[-1]:
                        sell_signals += 1

        total = buy_signals + sell_signals
        if buy_signals > sell_signals and total >= 2:
            summary = "买入信号"
        elif sell_signals > buy_signals and total >= 2:
            summary = "卖出信号"
        elif buy_signals > 0:
            summary = "偏买入"
        elif sell_signals > 0:
            summary = "偏卖出"
        else:
            summary = "中性"

        return {
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "summary": summary
        }
