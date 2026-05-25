from datetime import datetime
from typing import Optional

import pandas as pd

from data.store import DataStore
from data.generator import generate_stock_data, SAMPLE_STOCKS, generate_sample_data
from config.settings import DEFAULT_START_DATE, DEFAULT_END_DATE

_network_available = None
_hist_network_available = None


def _check_network():
    global _network_available
    if _network_available is not None:
        return _network_available
    try:
        import akshare as ak
        import threading
        result = [None]
        
        def check():
            try:
                df = ak.stock_info_a_code_name()
                result[0] = not df.empty
            except:
                result[0] = False
        
        t = threading.Thread(target=check)
        t.daemon = True
        t.start()
        t.join(timeout=5)
        
        _network_available = result[0] if result[0] is not None else False
    except Exception:
        _network_available = False
    return _network_available


def _check_hist_network():
    global _hist_network_available
    if _hist_network_available is not None:
        return _hist_network_available
    try:
        import akshare as ak
        import threading
        result = [None]
        
        def check():
            try:
                df = ak.stock_zh_a_hist(symbol="600519", period="daily",
                                        start_date="20240101", end_date="20240110", adjust="qfq")
                result[0] = not df.empty
            except:
                result[0] = False
        
        t = threading.Thread(target=check)
        t.daemon = True
        t.start()
        t.join(timeout=5)
        
        _hist_network_available = result[0] if result[0] is not None else False
    except Exception:
        _hist_network_available = False
    return _hist_network_available


class DataFetcher:
    def __init__(self):
        self.store = DataStore()
        self._generated_codes = set()
        if _check_network() and not _check_hist_network():
            from data.generator import generate_sample_data
            generate_sample_data()
            self.store.save_basic(self._build_local_stock_df())

    def fetch_stock_list(self):
        if _check_network() and _check_hist_network():
            import threading
            result = [None]
            
            def fetch():
                try:
                    import akshare as ak
                    df = ak.stock_info_a_code_name()
                    if "证券代码" in df.columns and "证券简称" in df.columns:
                        df = df.rename(columns={"证券代码": "code", "证券简称": "name"})
                    elif "code" not in df.columns:
                        result[0] = self._get_local_stock_list()
                        return
                    df["code"] = df["code"].astype(str).str.zfill(6)
                    df["industry"] = ""
                    df["market"] = df["code"].apply(
                        lambda x: "sh" if x.startswith("6") else ("sz" if not x.startswith("8") else "bj")
                    )
                    df["list_date"] = ""
                    self.store.save_basic(df)
                    result[0] = df
                except Exception as e:
                    print(f"获取股票列表失败: {e}")
                    result[0] = self._get_local_stock_list()
            
            t = threading.Thread(target=fetch)
            t.daemon = True
            t.start()
            t.join(timeout=10)
            
            if result[0] is not None:
                return result[0]
        
        return self._get_local_stock_list()

    def _build_local_stock_df(self):
        records = []
        for code, name in SAMPLE_STOCKS:
            records.append({
                "code": code, "name": name, "industry": "",
                "market": "sz" if code.startswith("0") or code.startswith("3") else "sh",
                "list_date": "20000101"
            })
        return pd.DataFrame(records)

    def _get_local_stock_list(self):
        df = self._build_local_stock_df()
        self.store.save_basic(df)
        return df

    def fetch_daily(self, code: str, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        use_network = _check_network() and _check_hist_network()
        if use_network:
            import akshare as ak
            try:
                df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                        start_date=start, end_date=end, adjust="qfq")
                if df.empty:
                    return df
                df.columns = [col.strip() for col in df.columns]
                df = df.rename(columns={
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"
                })
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
                self.store.save_daily(df, code)
                return df
            except Exception as e:
                print(f"网络获取 {code} 失败: {e}")
        df = generate_stock_data(code, start=start.replace("-", ""), end=end.replace("-", ""))
        if not df.empty:
            self.store.save_daily(df, code)
            self._generated_codes.add(code)
        return df

    def get_daily_data(self, code: str, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        if not df.empty:
            return df
        raw = self.fetch_daily(code, start, end)
        if raw.empty:
            return pd.DataFrame()
        df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        return df

    def ensure_data(self, code: str, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        if len(df) < 60:
            self.fetch_daily(code, start, end)
            df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        return df

    def ensure_all_sample_data(self, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE):
        from data.generator import generate_sample_data
        generate_sample_data(start, end)
        self._use_local = True

    def fetch_index_daily(self, index_code: str = "000001",
                          start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            if not df.empty:
                df = df.rename(columns={
                    "date": "date", "open": "open", "high": "high",
                    "low": "low", "close": "close", "volume": "volume"
                })
                df["code"] = index_code
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                mask = (df["date"] >= start.replace("-", "")) & (df["date"] <= end.replace("-", ""))
                df = df[mask]
            return df
        except Exception as e:
            print(f"获取指数数据失败: {e}")
            return pd.DataFrame()

    def fetch_fundamental(self, code: str):
        try:
            df = ak.stock_financial_abstract(symbol=code)
            if not df.empty:
                return df.head(4)
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def close(self):
        self.store.close()
