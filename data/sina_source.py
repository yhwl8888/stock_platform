import requests
import re
import json
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime


SINA_REALTIME_URL = "https://hq.sinajs.cn/list="
SINA_KLINE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"


def _get_sina_code(code: str) -> str:
    code = code.strip().zfill(6)
    if code.startswith("6") or code.startswith("5") or code.startswith("9"):
        return f"sh{code}"
    elif code.startswith("0") or code.startswith("3") or code.startswith("1"):
        return f"sz{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"bj{code}"
    return f"sh{code}"


def fetch_sina_realtime(codes: List[str], timeout: float = 10.0) -> Dict[str, dict]:
    if not codes:
        return {}

    sina_codes = [_get_sina_code(c) for c in codes]
    url = SINA_REALTIME_URL + ",".join(sina_codes)

    result = {}
    try:
        headers = {"Referer": "https://finance.sina.com.cn"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        text = resp.text

        for sina_code in sina_codes:
            pattern = f'var hq_str_{sina_code}="([^"]*)"'
            match = re.search(pattern, text)
            if not match or not match.group(1):
                continue

            fields = match.group(1).split(",")
            if len(fields) < 32:
                continue

            raw_code = sina_code[2:]
            try:
                name = fields[0].strip()
                open_price = float(fields[1]) if fields[1] else 0
                pre_close = float(fields[2]) if fields[2] else 0
                price = float(fields[3]) if fields[3] else 0
                high = float(fields[4]) if fields[4] else 0
                low = float(fields[5]) if fields[5] else 0
                volume = float(fields[8]) if fields[8] else 0

                change_pct = 0
                if pre_close > 0 and price > 0:
                    change_pct = ((price - pre_close) / pre_close) * 100

                if price > 0:
                    result[raw_code] = {
                        "code": raw_code,
                        "name": name,
                        "price": round(price, 2),
                        "pre_close": round(pre_close, 2),
                        "open": round(open_price, 2),
                        "high": round(high, 2),
                        "low": round(low, 2),
                        "volume": int(volume),
                        "change_pct": round(change_pct, 2),
                        "source": "sina",
                    }
            except (ValueError, IndexError):
                continue

    except Exception as e:
        print(f"Sina realtime API error: {e}")

    return result


def fetch_sina_daily(code: str, start: str = "20200101", end: str = "20251231") -> pd.DataFrame:
    code = code.strip().zfill(6)
    sina_code = _get_sina_code(code)

    try:
        params = {
            "symbol": sina_code,
            "scale": 240,
            "ma": "no",
            "datalen": 1023,
        }
        headers = {"Referer": "https://finance.sina.com.cn"}
        resp = requests.get(SINA_KLINE_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()

        data = json.loads(resp.text)
        if not data:
            return pd.DataFrame()

        records = []
        for item in data:
            day = item.get("day", "")
            if not day:
                continue
            date_str = day.replace("-", "")
            start_clean = start.replace("-", "")
            end_clean = end.replace("-", "")
            if date_str < start_clean or date_str > end_clean:
                continue
            records.append({
                "date": date_str,
                "open": float(item.get("open", 0)),
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "close": float(item.get("close", 0)),
                "volume": float(item.get("volume", 0)),
                "amount": 0,
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    except Exception as e:
        print(f"Sina daily API error for {code}: {e}")
        return pd.DataFrame()


def check_sina_network(timeout: float = 3.0) -> bool:
    try:
        headers = {"Referer": "https://finance.sina.com.cn"}
        resp = requests.get(
            f"{SINA_REALTIME_URL}sh600519",
            headers=headers,
            timeout=timeout,
        )
        return resp.status_code == 200 and "hq_str_sh600519" in resp.text
    except Exception:
        return False
