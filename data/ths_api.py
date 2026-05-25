# -*- coding: utf-8 -*-
"""Tonghuashun (THS) API - northbound capital + EPS forecast"""
import requests
import pandas as pd

HSGT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.hexin.cn/",
}


def northbound_realtime() -> pd.DataFrame:
    """Northbound capital flow realtime (北向资金实时, 262 time points)
    Returns DataFrame: time, hgt_yi(沪股通净流入/亿), sgt_yi(深股通净流入/亿)
    """
    url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
    try:
        r = requests.get(url, headers=HSGT_HEADERS, timeout=10)
        d = r.json()
    except Exception:
        return pd.DataFrame()
    times = d.get("time", [])
    hgt = d.get("hgt", [])
    sgt = d.get("sgt", [])
    n = len(times)
    return pd.DataFrame({
        "time": times,
        "hgt_yi": hgt[:n] + [None] * (n - len(hgt)),
        "sgt_yi": sgt[:n] + [None] * (n - len(sgt)),
    })


def eps_forecast(code: str) -> pd.DataFrame:
    """Institutional consensus EPS forecast (同花顺一致预期EPS)
    Returns DataFrame: year, min, avg, max, median
    """
    url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://basic.10jqka.com.cn/",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = "gbk"
        dfs = pd.read_html(r.text)
        for df in dfs:
            cols = [str(c) for c in df.columns]
            if any("每股收益" in c or "均值" in c for c in cols):
                return df
        return dfs[0] if dfs else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
