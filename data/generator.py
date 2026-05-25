import numpy as np
import pandas as pd
from data.full_stock_list import FULL_STOCK_LIST
from datetime import datetime, timedelta


REALISTIC_PRICES = {
    "600519": 1580, "000858": 135, "002304": 110, "000568": 140,
    "600809": 200, "600276": 42, "600436": 220, "300750": 200,
    "002594": 280, "300760": 280, "002415": 32, "002475": 36,
    "000333": 68, "000651": 42, "000725": 4.5, "600036": 38,
    "601318": 55, "600030": 22, "601166": 20, "601398": 7,
    "600887": 28, "600900": 30, "600585": 28, "601088": 42,
    "601857": 10, "002714": 48, "002352": 42, "002230": 48,
    "002371": 350, "002920": 100, "300059": 18, "300124": 65,
    "300015": 14, "300033": 175, "300274": 80, "300308": 120,
    "300413": 22, "300433": 20, "300498": 18, "300502": 100,
    "300782": 80, "600690": 28, "600941": 110, "601127": 100,
    "601899": 18, "688041": 100, "688111": 280, "688256": 150,
    "688981": 70, "002007": 18, "002270": 18,
}


def generate_stock_data(code: str, name: str = "",
                        start: str = "20200101", end: str = "20251231",
                        base_price: float = None) -> pd.DataFrame:
    start_dt = datetime.strptime(start, "%Y%m%d") if len(start) == 8 else datetime.strptime(start.replace("-", ""), "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d") if len(end) == 8 else datetime.strptime(end.replace("-", ""), "%Y%m%d")

    if base_price is None:
        code_num = code.strip().zfill(6)
        first_char = code_num[0]
        try:
            base_price = REALISTIC_PRICES.get(code, {3: 20, 6: 60, 0: 15, 2: 8, 8: 15}.get(int(first_char), 10) * 10)
        except ValueError:
            base_price = 20.0

    dates = pd.bdate_range(start_dt, end_dt)
    if len(dates) < 20:
        return pd.DataFrame()

    n = len(dates)
    try:
        np.random.seed(int(code.strip().zfill(6)))
    except ValueError:
        np.random.seed(hash(code) % 10000)

    raw = np.cumsum(np.random.randn(n) * 0.012)
    raw = raw - np.linspace(raw[0], raw[-1], n)
    max_dev = np.max(np.abs(raw))
    if max_dev > 0:
        raw = raw / max_dev * 0.15
    prices = base_price * (1 + raw)
    prices = np.maximum(prices, base_price * 0.5)

    daily_vol = base_price * 0.015
    opens = prices + np.random.randn(n) * daily_vol * 0.5
    highs = np.maximum(opens, prices) + abs(np.random.randn(n) * daily_vol * 0.6)
    lows = np.minimum(opens, prices) - abs(np.random.randn(n) * daily_vol * 0.6)
    closes = prices
    volumes = (np.random.rand(n) * 0.5 + 0.5) * 2000000 * (prices / base_price)
    amounts = volumes * closes

    df = pd.DataFrame({
        "date": dates.strftime("%Y%m%d"),
        "open": np.round(np.maximum(opens, 0.01), 2),
        "high": np.round(np.maximum(highs, 0.01), 2),
        "low": np.round(np.maximum(lows, 0.01), 2),
        "close": np.round(np.maximum(closes, 0.01), 2),
        "volume": np.round(volumes, 0).astype(int),
        "amount": np.round(amounts, 0).astype(int),
    })
    return df


# SAMPLE_STOCKS is now backed by FULL_STOCK_LIST from full_stock_list.py
# Kept as alias for backward compatibility
SAMPLE_STOCKS = FULL_STOCK_LIST


def generate_sample_data(start: str = "20200101", end: str = "20251231",
                         stock_list: list = None) -> dict[str, pd.DataFrame]:
    from data.store import DataStore
    store = DataStore()

    data = {}
    stocks = stock_list or SAMPLE_STOCKS
    basic_records = []

    for code, name in stocks:
        df = generate_stock_data(code, name, start, end)
        if not df.empty:
            store.save_daily(df, code)
            data[code] = store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        basic_records.append({"code": code, "name": name, "industry": "",
                              "market": "sz" if code.startswith("0") or code.startswith("3") else "sh",
                              "list_date": "20000101", "last_update": datetime.now().strftime("%Y-%m-%d")})

    basic_df = pd.DataFrame(basic_records)
    store.save_basic(basic_df)
    store.close()
    return data


def load_csv_data(filepath: str, code: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    required = {"date", "open", "high", "low", "close", "volume"}
    df.columns = [c.strip().lower() for c in df.columns]
    if not required.issubset(df.columns):
        alt_map = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume"}
        df = df.rename(columns=alt_map)
    if not required.issubset(df.columns):
        raise ValueError(f"CSV必须包含列: {required}")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
    from data.store import DataStore
    store = DataStore()
    store.save_daily(df, code)
    store.close()
    return df
