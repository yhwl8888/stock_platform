import numpy as np


def ma_crossover(close, high, low, i, position, **params):
    if i < 20 or position != 0:
        return 0
    ma5 = np.mean(close[i - 4:i + 1])
    ma20 = np.mean(close[i - 19:i + 1])
    ma5_prev = np.mean(close[i - 5:i])
    ma20_prev = np.mean(close[i - 20:i])
    if ma5_prev <= ma20_prev and ma5 > ma20:
        return 1
    return 0


def ma_crossover_exit(close, high, low, i, entry_price, position, entry_bar, **params):
    if position > 0 and i >= entry_bar + 5:
        ma5 = np.mean(close[i - 4:i + 1])
        ma20 = np.mean(close[i - 19:i + 1])
        if ma5 < ma20:
            return -1
    return 0


def dual_thrust(close, high, low, i, position, **params):
    if i < 5 or position != 0:
        return 0
    prev_high = high[i - 4:i + 1]
    prev_low = low[i - 4:i + 1]
    prev_close = close[i - 4:i + 1]
    hh = np.max(prev_high)
    lc = np.min(prev_close)
    hc = np.max(prev_close)
    ll = np.min(prev_low)
    r1 = hh - lc
    r2 = hc - ll
    r = max(r1, r2)
    if r == 0:
        return 0
    k = params.get("k", 0.5)
    upper = close[i - 1] + k * r
    lower = close[i - 1] - (1 - k) * r
    if close[i] > upper:
        return 1
    elif close[i] < lower:
        return -1
    return 0


def dual_thrust_exit(close, high, low, i, entry_price, position, entry_bar, **params):
    lookback = params.get("dual_thrust_hold", 3)
    if position != 0 and i >= entry_bar + lookback:
        return -position
    if position > 0:
        stop_loss = entry_price * (1 - params.get("stop_loss_pct", 0.03))
        if close[i] < stop_loss:
            return -1
        take_profit = entry_price * (1 + params.get("take_profit_pct", 0.05))
        if close[i] > take_profit:
            return -1
    return 0


def heikin_ashi(close, high, low, i, position, **params):
    if i < 2:
        return 0

    def ha_transform(idx):
        ha_close = (open_p[idx] + close[idx] + high[idx] + low[idx]) / 4
        return ha_close

    open_p = np.full(len(close), np.nan)
    open_p[0] = close[0]
    for j in range(1, len(close)):
        ha_close_prev = (open_p[j - 1] + close[j - 1] + high[j - 1] + low[j - 1]) / 4
        open_p[j] = (open_p[j - 1] + ha_close_prev) / 2

    ha_open = open_p[i]
    ha_close = (open_p[i] + close[i] + high[i] + low[i]) / 4
    ha_high = max(ha_open, ha_close, high[i])
    ha_low = min(ha_open, ha_close, low[i])

    ha_open_prev = open_p[i - 1]
    ha_close_prev = (open_p[i - 1] + close[i - 1] + high[i - 1] + low[i - 1]) / 4

    body = abs(ha_open - ha_close)
    body_prev = abs(ha_open_prev - ha_close_prev)

    is_green = ha_close > ha_open
    is_red = ha_open > ha_close
    is_marubozu_green = is_green and ha_open == ha_low
    is_marubozu_red = is_red and ha_open == ha_high
    body_growing = body > body_prev

    if is_marubozu_green and body_growing and ha_open_prev > ha_close_prev:
        return 1
    if position < 0:
        if is_marubozu_red and ha_open_prev < ha_close_prev:
            return 1
    if is_marubozu_red and body_growing and ha_open_prev < ha_close_prev:
        return -1
    if position > 0:
        if is_marubozu_green and ha_open_prev > ha_close_prev:
            return -1
    return 0


def heikin_ashi_exit(close, high, low, i, entry_price, position, entry_bar, **params):
    return 0


def parabolic_sar(close, high, low, i, position, **params):
    if i < 3:
        return 0

    def calc_sar(data_high, data_low, data_close):
        n = len(data_close)
        sar = np.zeros(n)
        trend = np.zeros(n, dtype=int)
        ep = np.zeros(n)
        af = np.zeros(n)

        initial_af = 0.02
        step_af = 0.02
        end_af = 0.2

        trend[1] = 1 if data_close[1] > data_close[0] else -1
        sar[1] = data_low[0] if trend[1] > 0 else data_high[0]
        ep[1] = data_high[1] if trend[1] > 0 else data_low[1]
        af[1] = initial_af

        for j in range(2, n):
            temp = sar[j - 1] + af[j - 1] * (ep[j - 1] - sar[j - 1])
            if trend[j - 1] < 0:
                sar[j] = max(temp, data_high[j - 1], data_high[j - 2])
                trend[j] = 1 if sar[j] < data_high[j] else trend[j - 1] - 1
            else:
                sar[j] = min(temp, data_low[j - 1], data_low[j - 2])
                trend[j] = -1 if sar[j] > data_low[j] else trend[j - 1] + 1

            if trend[j] < 0:
                ep[j] = min(data_low[j], ep[j - 1]) if trend[j] != -1 else data_low[j]
            else:
                ep[j] = max(data_high[j], ep[j - 1]) if trend[j] != 1 else data_high[j]

            if abs(trend[j]) == 1:
                af[j] = initial_af
            else:
                if ep[j] == ep[j - 1]:
                    af[j] = af[j - 1]
                else:
                    af[j] = min(end_af, af[j - 1] + step_af)

        return sar, trend

    sar_vals, trend = calc_sar(
        high[:i + 1], low[:i + 1], close[:i + 1]
    )

    if trend[i] > 0 and sar_vals[i] < close[i]:
        if position <= 0:
            return 1
    elif trend[i] < 0 and sar_vals[i] > close[i]:
        if position >= 0:
            return -1
    return 0


def parabolic_sar_exit(close, high, low, i, entry_price, position, entry_bar, **params):
    return 0


STRATEGIES = {
    "ma_crossover": {
        "name": "MA5/MA20 金叉",
        "desc": "MA5上穿MA20买入，下穿卖出",
        "signal": ma_crossover,
        "exit": ma_crossover_exit,
        "params": {},
        "default": True,
    },
    "dual_thrust": {
        "name": "Dual Thrust 通道突破",
        "desc": "基于前N日高低收范围设定突破通道",
        "signal": dual_thrust,
        "exit": dual_thrust_exit,
        "params": {"k": 0.5, "dual_thrust_hold": 3, "stop_loss_pct": 0.03, "take_profit_pct": 0.05},
    },
    "heikin_ashi": {
        "name": "Heikin-Ashi 均值K线",
        "desc": "Heikin-Ashi蜡烛图形态识别",
        "signal": heikin_ashi,
        "exit": heikin_ashi_exit,
        "params": {},
    },
    "parabolic_sar": {
        "name": "Parabolic SAR 抛物线",
        "desc": "抛物线指标趋势跟踪",
        "signal": parabolic_sar,
        "exit": parabolic_sar_exit,
        "params": {},
    },
}


def get_strategy(name):
    if name in STRATEGIES:
        return STRATEGIES[name]
    return STRATEGIES["ma_crossover"]