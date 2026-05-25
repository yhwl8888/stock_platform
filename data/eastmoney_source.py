import requests
import json
from typing import Dict, List
import pandas as pd


EASTMONEY_REALTIME_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


def _get_secid(code: str) -> str:
    code = code.strip().zfill(6)
    if code.startswith("6") or code.startswith("5") or code.startswith("9"):
        return f"1.{code}"
    elif code.startswith("0") or code.startswith("3") or code.startswith("1"):
        return f"0.{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"0.{code}"
    return f"1.{code}"


def fetch_eastmoney_realtime(codes: List[str], timeout: float = 10.0) -> Dict[str, dict]:
    if not codes:
        return {}

    secids = [_get_secid(c) for c in codes]

    result = {}
    try:
        params = {
            "fltt": 2,
            "invt": 2,
            "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18",
            "secids": ",".join(secids),
        }
        headers = {"Referer": "https://quote.eastmoney.com"}
        resp = requests.get(EASTMONEY_REALTIME_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        diff = data.get("data", {}).get("diff", [])
        if not diff:
            return result

        for item in diff:
            raw_code = str(item.get("f12", "")).zfill(6)
            try:
                price = float(item.get("f2", 0)) if item.get("f2") != "-" else 0
                change_pct = float(item.get("f3", 0)) if item.get("f3") != "-" else 0
                volume = float(item.get("f5", 0)) if item.get("f5") != "-" else 0
                open_price = float(item.get("f17", 0)) if item.get("f17") != "-" else 0
                high = float(item.get("f15", 0)) if item.get("f15") != "-" else 0
                low = float(item.get("f16", 0)) if item.get("f16") != "-" else 0
                pre_close = float(item.get("f18", 0)) if item.get("f18") != "-" else 0

                if price > 0:
                    result[raw_code] = {
                        "code": raw_code,
                        "name": str(item.get("f14", "")),
                        "price": round(price, 2),
                        "pre_close": round(pre_close, 2),
                        "open": round(open_price, 2),
                        "high": round(high, 2),
                        "low": round(low, 2),
                        "volume": int(volume),
                        "change_pct": round(change_pct, 2),
                        "source": "eastmoney",
                    }
            except (ValueError, TypeError):
                continue

    except Exception as e:
        print(f"Eastmoney realtime API error: {e}")

    return result


def fetch_eastmoney_daily(code: str, start: str = "20200101", end: str = "20251231") -> pd.DataFrame:
    code = code.strip().zfill(6)
    secid = _get_secid(code)

    try:
        start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:8]}" if len(start) == 8 else start
        end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:8]}" if len(end) == 8 else end

        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101,
            "fqt": 1,
            "beg": start_fmt,
            "end": end_fmt,
        }
        headers = {"Referer": "https://quote.eastmoney.com"}
        resp = requests.get(EASTMONEY_KLINE_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        klines = data.get("data", {}).get("klines", [])
        if not klines:
            return pd.DataFrame()

        records = []
        for line in klines:
            fields = line.split(",")
            if len(fields) < 7:
                continue
            records.append({
                "date": fields[0].replace("-", ""),
                "open": float(fields[1]),
                "close": float(fields[2]),
                "high": float(fields[3]),
                "low": float(fields[4]),
                "volume": float(fields[5]),
                "amount": float(fields[6]),
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    except Exception as e:
        print(f"Eastmoney daily API error for {code}: {e}")
        return pd.DataFrame()


def check_eastmoney_network(timeout: float = 3.0) -> bool:
    try:
        params = {
            "fltt": 2,
            "invt": 2,
            "fields": "f2,f12,f14",
            "secids": "1.600519",
        }
        headers = {"Referer": "https://quote.eastmoney.com"}
        resp = requests.get(EASTMONEY_REALTIME_URL, params=params, headers=headers, timeout=timeout)
        data = resp.json()
        return resp.status_code == 200 and data.get("data") is not None
    except Exception:
        return False
