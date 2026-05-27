import requests
import re
import json
import pandas as pd
import numpy as np
import codecs
import time
import logging
from datetime import datetime
from typing import Optional
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
TENCENT_HISTORY_URL = "https://web.ifzq.gtimg.cn/appstock/app/minute/query"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _get_qcode(code: str) -> str:
    code = code.strip().lower()
    if code.startswith(("sh", "sz", "bj")) and len(code) == 8:
        return code
    bare = code.zfill(6)
    if bare.startswith(("6", "5", "9")):
        return f"sh{bare}"
    elif bare.startswith(("0", "3", "1")):
        return f"sz{bare}"
    elif bare.startswith(("8", "4")):
        return f"bj{bare}"
    return f"sh{bare}"


def fetch_realtime_quote(code: str) -> Optional[dict]:
    qcode = _get_qcode(code)
    market = qcode[:2]
    bare = qcode[2:]

    result = _do_fetch_quote(market, bare)
    if result:
        return result

    if bare.startswith("0") or bare.startswith("3"):
        other = "sh" if market == "sz" else "sz"
        result = _do_fetch_quote(other, bare)
        if result:
            return result

    return None


def _do_fetch_quote(market: str, bare: str) -> Optional[dict]:
    qcode = f"{market}{bare}"
    try:
        resp = requests.get(
            TENCENT_QUOTE_URL + qcode,
            headers={"User-Agent": USER_AGENT},
            timeout=5,
        )
        text = resp.text
        key = f"v_{qcode}"
        if key not in text:
            return None
        match = re.search(f'{key}="([^"]+)"', text)
        if not match:
            return None
        fields = match.group(1).split("~")
        if len(fields) < 50:
            return None
        return {
            "code": fields[2].strip().zfill(6),
            "name": fields[1].strip(),
            "price": float(fields[3]) if fields[3] else 0,
            "pre_close": float(fields[4]) if fields[4] else 0,
            "open": float(fields[5]) if fields[5] else 0,
            "volume": float(fields[6]) if fields[6] else 0,
            "high": float(fields[33]) if fields[33] else 0,
            "low": float(fields[34]) if fields[34] else 0,
            "change_pct": round(((float(fields[3]) - float(fields[4])) / float(fields[4]) * 100), 2) if fields[3] and fields[4] and float(fields[4]) > 0 else 0,
        }
    except Exception:
        return None


def _fetch_kline_raw(code: str, days: int = 250) -> list:
    qcode = _get_qcode(code)
    market = qcode[:2]
    bare = qcode[2:]

    if market == "bj":
        return []

    result = _do_fetch_kline(market, bare, days)
    if result:
        return result

    if bare.startswith("0") or bare.startswith("3"):
        other = "sh" if market == "sz" else "sz"
        result = _do_fetch_kline(other, bare, days)
        if result:
            return result

    return []


def _do_fetch_kline(market: str, bare: str, days: int) -> list:
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={market}{bare},day,,,{days},,qfq"
    for attempt in range(3):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
            data = resp.json()
            if data.get("code") != 0:
                logger.warning(f"K线API返回非0 code: {data.get('code')}, url={url}")
                return []

            kline_data = data.get("data", {})
            stock_data = kline_data.get(f"{market}{bare}", kline_data)
            days_data = stock_data.get("day", [])

            if not days_data:
                logger.warning(f"K线数据为空: {market}{bare}, 尝试 {attempt+1}/3")
                if attempt < 2:
                    time.sleep(1)
                    continue
                return []

            result = []
            for item in days_data:
                if len(item) >= 6:
                    result.append({
                        "date": str(item[0]),
                        "open": float(item[1]),
                        "close": float(item[2]),
                        "high": float(item[3]),
                        "low": float(item[4]),
                        "volume": float(item[5]),
                    })
            logger.info(f"K线获取成功: {market}{bare}, {len(result)}条")
            return result
        except requests.exceptions.Timeout:
            logger.warning(f"K线请求超时: {market}{bare}, 尝试 {attempt+1}/3")
            if attempt < 2:
                time.sleep(2)
        except Exception as e:
            logger.error(f"K线获取异常: {market}{bare}, {e}, 尝试 {attempt+1}/3")
            if attempt < 2:
                time.sleep(1)
    return []


def fetch_kline(code: str, days: int = 250) -> list:
    """K线获取 - 不使用 lru_cache，避免缓存失败结果"""
    return _fetch_kline_raw(code, days)


def search_stocks(keyword: str) -> list:
    kw = keyword.strip()
    if not kw:
        return []

    results = []

    try:
        url = f"https://smartbox.gtimg.cn/s3/?q={kw}&t=all"
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
        text = resp.text
        if '="' in text and not text.startswith('v_hint="N"'):
            matches = re.findall(r'"(.*?)"', text)
            for m in matches:
                entries = m.split("^")
                for entry in entries:
                    parts = entry.split("~")
                    if len(parts) >= 5 and parts[0] in ("sh", "sz", "bj"):
                        raw_name = parts[2].strip()
                        try:
                            raw_name = codecs.decode(raw_name, 'unicode_escape')
                        except Exception:
                            pass
                        results.append({
                            "code": parts[1].strip().zfill(6),
                            "name": raw_name,
                            "market": parts[0].strip(),
                        })
    except Exception:
        pass

    if results:
        return results

    if kw.isdigit() and len(kw) >= 4:
        code = kw.zfill(6)
        try:
            qcode = _get_qcode(code)
            resp = requests.get(
                TENCENT_QUOTE_URL + qcode,
                headers={"User-Agent": USER_AGENT},
                timeout=5,
            )
            text = resp.text
            key = f"v_{qcode}"
            if key in text:
                match = re.search(f'{key}="([^"]+)"', text)
                if match:
                    fields = match.group(1).split("~")
                    if len(fields) >= 3 and fields[1].strip():
                        results.append({
                            "code": fields[2].strip().zfill(6),
                            "name": fields[1].strip(),
                            "market": "sh" if code.startswith(("6", "5")) else "sz",
                        })
                        return results
        except Exception:
            pass

        name_map = {"6": "上海", "0": "深圳", "3": "创业板", "8": "北京", "4": "北京", "5": "上海"}
        prefix = code[0]
        market_name = name_map.get(prefix, "")
        results.append({
            "code": code,
            "name": f"{kw}",
            "market": "sh" if code.startswith(("6", "5", "9")) else "sz",
        })

    return results
