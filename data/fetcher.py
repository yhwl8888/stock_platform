from datetime import datetime, timedelta
from typing import Optional, Dict
from collections import OrderedDict
import threading
import concurrent.futures

import pandas as pd

from data.store import DataStore
from data.market_utils import parse_code, is_index, get_full_code
from data.generator import generate_stock_data, SAMPLE_STOCKS, generate_sample_data
from data.sina_source import fetch_sina_daily, check_sina_network
from data.eastmoney_source import fetch_eastmoney_daily, check_eastmoney_network
from config.settings import DEFAULT_START_DATE, DEFAULT_END_DATE

_network_available = None
_hist_network_available = None
_sina_network_available = None
_eastmoney_network_available = None


# Memory cache: {cache_key: (timestamp, DataFrame)}
_memory_cache: OrderedDict = OrderedDict()
_memory_cache_lock = threading.Lock()
_MEMORY_CACHE_MAX = 50
_MEMORY_CACHE_TTL_MINUTES = 30


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


def _check_sina_network():
    global _sina_network_available
    if _sina_network_available is not None:
        return _sina_network_available
    try:
        _sina_network_available = check_sina_network(timeout=5)
    except Exception:
        _sina_network_available = False
    return _sina_network_available


def _check_eastmoney_network():
    global _eastmoney_network_available
    if _eastmoney_network_available is not None:
        return _eastmoney_network_available
    try:
        _eastmoney_network_available = check_eastmoney_network(timeout=5)
    except Exception:
        _eastmoney_network_available = False
    return _eastmoney_network_available


def _get_cache_key(code: str, start: str, end: str) -> str:
    return f"{code}|{start}|{end}"


def _memory_cache_get(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    key = _get_cache_key(code, start, end)
    with _memory_cache_lock:
        if key not in _memory_cache:
            return None
        ts, df = _memory_cache[key]
        if datetime.now() - ts > timedelta(minutes=_MEMORY_CACHE_TTL_MINUTES):
            del _memory_cache[key]
            return None
        _memory_cache.move_to_end(key)
        return df.copy()


def _memory_cache_put(code: str, start: str, end: str, df: pd.DataFrame):
    if df is None or df.empty:
        return
    key = _get_cache_key(code, start, end)
    with _memory_cache_lock:
        _memory_cache[key] = (datetime.now(), df.copy())
        _memory_cache.move_to_end(key)
        while len(_memory_cache) > _MEMORY_CACHE_MAX:
            _memory_cache.popitem(last=False)


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
                    if "\u8bc1\u5238\u4ee3\u7801" in df.columns and "\u8bc1\u5238\u7b80\u79f0" in df.columns:
                        df = df.rename(columns={"\u8bc1\u5238\u4ee3\u7801": "code", "\u8bc1\u5238\u7b80\u79f0": "name"})
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
                    print(f"\u83b7\u53d6\u80a1\u7968\u5217\u8868\u5931\u8d25: {e}")
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

    def _try_fetch_from_source(self, code: str, start: str, end: str, source_name: str) -> pd.DataFrame:
        start_clean = start.replace("-", "")
        end_clean = end.replace("-", "")
        try:
            if source_name == "akshare":
                import akshare as ak
                df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                        start_date=start_clean, end_date=end_clean, adjust="qfq")
                if df.empty:
                    return pd.DataFrame()
                df.columns = [col.strip() for col in df.columns]
                df = df.rename(columns={
                    "\u65e5\u671f": "date", "\u5f00\u76d8": "open", "\u6536\u76d8": "close",
                    "\u6700\u9ad8": "high", "\u6700\u4f4e": "low", "\u6210\u4ea4\u91cf": "volume", "\u6210\u4ea4\u989d": "amount"
                })
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
                return df

            elif source_name == "sina":
                df = fetch_sina_daily(code, start_clean, end_clean)
                return df

            elif source_name == "eastmoney":
                df = fetch_eastmoney_daily(code, start_clean, end_clean)
                return df

            elif source_name == "local":
                df = generate_stock_data(code, start=start_clean, end=end_clean)
                return df

        except Exception as e:
            print(f"[{source_name}] fetch {code} failed: {e}")

        return pd.DataFrame()

    def fetch_daily(self, code: str, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        cached = _memory_cache_get(code, start, end)
        if cached is not None:
            return cached

        df = pd.DataFrame()
        used_source = None

        # Fallback chain: AKShare -> Sina -> Eastmoney -> local generator
        sources = []
        if _check_network() and _check_hist_network():
            sources.append("akshare")
        if _check_sina_network():
            sources.append("sina")
        if _check_eastmoney_network():
            sources.append("eastmoney")
        sources.append("local")

        for source_name in sources:
            df = self._try_fetch_from_source(code, start, end, source_name)
            if not df.empty:
                used_source = source_name
                break

        if not df.empty:
            self.store.save_daily(df, code)
            _memory_cache_put(code, start, end, df)
            if used_source == "local":
                self._generated_codes.add(code)

        return df

    def get_daily_data(self, code: str, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        cached = _memory_cache_get(code, start, end)
        if cached is not None:
            return cached

        df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        if not df.empty:
            _memory_cache_put(code, start, end, df)
            return df

        raw = self.fetch_daily(code, start, end)
        if raw.empty:
            return pd.DataFrame()

        df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        if not df.empty:
            _memory_cache_put(code, start, end, df)
        return df

    def ensure_data(self, code: str, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        if len(df) < 60:
            self.fetch_daily(code, start, end)
            df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        return df

    def fetch_daily_batch(self, codes: list, start: str = DEFAULT_START_DATE,
                          end: str = DEFAULT_END_DATE) -> Dict[str, pd.DataFrame]:
        results = {}
        to_fetch = []

        for code in codes:
            cached = _memory_cache_get(code, start, end)
            if cached is not None:
                results[code] = cached
                continue
            db_df = self.store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
            if not db_df.empty:
                _memory_cache_put(code, start, end, db_df)
                results[code] = db_df
            else:
                to_fetch.append(code)

        if not to_fetch:
            return results

        def _fetch_one(c):
            df = self.fetch_daily(c, start, end)
            return c, df

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_one, c): c for c in to_fetch}
            for future in concurrent.futures.as_completed(futures):
                try:
                    c, df = future.result()
                    if not df.empty:
                        results[c] = df
                except Exception as e:
                    print(f"Batch fetch error for {futures[future]}: {e}")

        return results

    def ensure_all_sample_data(self, start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE):
        from data.generator import generate_sample_data
        generate_sample_data(start, end)
        self._use_local = True

    def fetch_index_daily(self, index_code: str = "000001",
                          start: str = DEFAULT_START_DATE, end: str = DEFAULT_END_DATE) -> pd.DataFrame:
        try:
            # Support prefixed codes like sh000001
            if index_code.startswith(("sh", "sz")):
                symbol = index_code
            else:
                symbol = get_full_code(index_code)
                parsed = parse_code(index_code)
                if parsed.get("type") != "index":
                    symbol = f"sh{index_code}"
            df = ak.stock_zh_index_daily(symbol=symbol)
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
            print(f"\u83b7\u53d6\u6307\u6570\u6570\u636e\u5931\u8d25: {e}")
            return pd.DataFrame()

    def fetch_fundamental(self, code: str):
        try:
            df = ak.stock_financial_abstract(symbol=code)
            if not df.empty:
                return df.head(4)
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()


    def get_stock_info(self, code: str) -> dict:
        """Get stock info with market disambiguation."""
        parsed = parse_code(code)
        if parsed.get("ambiguous"):
            return parsed
        basic = self.store.get_basic()
        if not basic.empty:
            bare = parsed.get("code", code)
            match = basic[basic["code"] == bare]
            if not match.empty:
                parsed["name"] = match.iloc[0].get("name", "")
        return parsed

    def close(self):
        self.store.close()
