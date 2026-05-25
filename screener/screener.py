import pandas as pd
import numpy as np
from typing import Callable, Any


class FilterCondition:
    def __init__(self, name: str, desc: str, func: Callable):
        self.name = name
        self.desc = desc
        self.func = func

    def apply(self, df: pd.DataFrame) -> pd.Series:
        return self.func(df)


class StockScreener:
    def __init__(self, name_map: dict[str, str] = None):
        self.conditions: list[FilterCondition] = []
        self.name_map = name_map or {}

    def add_condition(self, condition: FilterCondition):
        self.conditions.append(condition)

    def add_conditions(self, conditions: list[FilterCondition]):
        self.conditions.extend(conditions)

    def add_custom(self, name: str, desc: str, func: Callable):
        self.conditions.append(FilterCondition(name, desc, func))

    def run(self, stock_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        results = []
        for code, df in stock_data.items():
            if df.empty or len(df) < 30:
                continue
            passed = True
            info = {"code": code, "name": self.name_map.get(code, ""), "date": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1])}
            for cond in self.conditions:
                try:
                    result = cond.apply(df)
                    if isinstance(result, tuple):
                        passed_flag, extra = result
                        info[cond.name] = extra
                    else:
                        passed_flag = bool(result.all() if hasattr(result, "all") else result)
                        info[cond.name] = passed_flag
                    if not passed_flag:
                        passed = False
                        break
                except Exception:
                    passed = False
                    info[cond.name] = False
                    break
            if passed:
                info["close"] = float(df["close"].iloc[-1])
                results.append(info)
        return pd.DataFrame(results) if results else pd.DataFrame()


def price_above_ma(period: int = 20):
    return FilterCondition(
        f"price_above_ma{period}",
        f"收盘价高于{period}日均线",
        lambda df: df["close"].iloc[-1] > df["close"].rolling(period).mean().iloc[-1]
    )


def price_below_ma(period: int = 20):
    return FilterCondition(
        f"price_below_ma{period}",
        f"收盘价低于{period}日均线",
        lambda df: df["close"].iloc[-1] < df["close"].rolling(period).mean().iloc[-1]
    )


def ma_cross_up(fast: int = 5, slow: int = 20):
    def check(df):
        fast_ma = df["close"].rolling(fast).mean()
        slow_ma = df["close"].rolling(slow).mean()
        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return False
        return fast_ma.iloc[-2] <= slow_ma.iloc[-2] and fast_ma.iloc[-1] > slow_ma.iloc[-1]
    return FilterCondition(f"ma_{fast}_{slow}_cross_up", f"MA{fast}上穿MA{slow}", check)


def rsi_range(period: int = 14, min_val: float = 0, max_val: float = 100):
    def calc_rsi(close):
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))
    return FilterCondition(
        f"rsi_{min_val}_{max_val}",
        f"RSI({period})在{min_val}-{max_val}之间",
        lambda df: min_val <= calc_rsi(df["close"]).iloc[-1] <= max_val
    )


def volume_ratio(ratio: float = 1.5):
    def check(df):
        if len(df) < 6:
            return False
        avg_vol = df["volume"].iloc[-6:-1].mean()
        return df["volume"].iloc[-1] > avg_vol * ratio
    return FilterCondition(f"vol_ratio_{ratio}", f"成交量大于{ratio}倍均量", check)


def kdj_golden_cross():
    def check(df):
        low_9 = df["low"].rolling(9).min()
        high_9 = df["high"].rolling(9).max()
        rsv = (df["close"] - low_9) / (high_9 - low_9).replace(0, np.nan) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        if len(k) < 2 or len(d) < 2:
            return False
        return k.iloc[-2] <= d.iloc[-2] and k.iloc[-1] > d.iloc[-1]
    return FilterCondition("kdj_golden", "KDJ金叉", check)


def macd_golden_cross():
    def check(df):
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        macd = 2 * (dif - dea)
        if len(macd) < 2:
            return False
        return macd.iloc[-2] < 0 and macd.iloc[-1] > 0
    return FilterCondition("macd_golden", "MACD零轴下方金叉", check)


def ma_multi_arrange(short: int = 5, mid: int = 20, long: int = 60):
    def check(df):
        if len(df) < long:
            return False
        ma_s = df["close"].rolling(short).mean()
        ma_m = df["close"].rolling(mid).mean()
        ma_l = df["close"].rolling(long).mean()
        return ma_s.iloc[-1] > ma_m.iloc[-1] > ma_l.iloc[-1]
    return FilterCondition(f"ma_{short}_{mid}_{long}_arrange", f"多头排列({short}>{mid}>{long})", check)


def price_change_pct(days: int = 5, min_pct: float = -5, max_pct: float = 5):
    def check(df):
        if len(df) < days + 1:
            return False
        pct = (df["close"].iloc[-1] / df["close"].iloc[-1 - days] - 1) * 100
        return min_pct <= pct <= max_pct
    return FilterCondition(f"pct_{days}d_{min_pct}_{max_pct}", f"{days}日涨跌幅{min_pct}%~{max_pct}%", check)


def turnover_ratio(min_pct: float = 1.0, max_pct: float = 10.0):
    def check(df):
        if len(df) < 2:
            return False
        latest = df.iloc[-1]
        if latest["amount"] == 0 or latest["close"] == 0:
            return False
        turnover = (latest["volume"] * latest["close"]) / (latest["amount"] / 10000 + 0.001) * 100
        return min_pct <= turnover <= max_pct
    return FilterCondition(f"turnover_{min_pct}_{max_pct}", f"换手率{min_pct}%~{max_pct}%", check)


def price_in_range(min_price: float = 0, max_price: float = 100):
    def check(df):
        if len(df) < 1:
            return False
        latest = df["close"].iloc[-1]
        return min_price <= latest <= max_price
    return FilterCondition(f"price_{min_price}_{max_price}", f"价格{min_price}~{max_price}元", check)


def ma_trend(period: int = 20, trend_days: int = 5):
    def check(df):
        if len(df) < period + trend_days:
            return False
        ma = df["close"].rolling(period).mean()
        return ma.iloc[-1] > ma.iloc[-1 - trend_days]
    return FilterCondition(f"ma_trend_{period}_{trend_days}", f"MA{period}向上 ({trend_days}日)", check)


def vol_ma_cross(fast: int = 5, slow: int = 20):
    def check(df):
        if len(df) < slow:
            return False
        vol_ma = df["volume"].rolling(slow).mean()
        if len(vol_ma) < fast:
            return False
        return df["volume"].iloc[-1] > vol_ma.iloc[-1] and df["volume"].iloc[-1 - 1] <= vol_ma.iloc[-1 - 1]
    return FilterCondition(f"vol_ma_{fast}_{slow}", f"成交量上穿均量", check)


builtin_filters = {
    "price_above_ma": {"label": "收盘价在均线上方", "builder": lambda **kw: price_above_ma(**kw) if kw else price_above_ma()},
    "price_below_ma": {"label": "收盘价在均线下方", "builder": lambda **kw: price_below_ma(**kw) if kw else price_below_ma()},
    "ma_cross_up": {"label": "均线金叉", "builder": lambda **kw: ma_cross_up(**kw) if kw else ma_cross_up()},
    "rsi_range": {"label": "RSI 区间", "builder": lambda **kw: rsi_range(**kw) if kw else rsi_range()},
    "volume_ratio": {"label": "放量", "builder": lambda **kw: volume_ratio(**kw) if kw else volume_ratio()},
    "kdj_golden": {"label": "KDJ 金叉", "builder": lambda **kw: kdj_golden_cross()},
    "macd_golden": {"label": "MACD 金叉", "builder": lambda **kw: macd_golden_cross()},
    "ma_arrange": {"label": "均线多头排列", "builder": lambda **kw: ma_multi_arrange(**kw) if kw else ma_multi_arrange()},
    "price_change": {"label": "涨跌幅区间", "builder": lambda **kw: price_change_pct(**kw) if kw else price_change_pct()},
    "turnover": {"label": "换手率区间", "builder": lambda **kw: turnover_ratio(**kw) if kw else turnover_ratio()},
    "price_range": {"label": "价格区间", "builder": lambda **kw: price_in_range(**kw) if kw else price_in_range()},
    "ma_trend": {"label": "均线趋势", "builder": lambda **kw: ma_trend(**kw) if kw else ma_trend()},
    "vol_ma_cross": {"label": "成交量金叉", "builder": lambda **kw: vol_ma_cross(**kw) if kw else vol_ma_cross()},
}

def get_filter_builder(name: str):
    entry = builtin_filters.get(name)
    if entry:
        return entry["builder"]
    return None

def get_filter_label(name: str):
    entry = builtin_filters.get(name)
    return entry["label"] if entry else name
