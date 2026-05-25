# -*- coding: utf-8 -*-
"""Eastmoney (dongfang caifu) API - direct HTTP, no wrapper dependency"""
import requests
from typing import List, Dict, Optional

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def _secid(code: str) -> str:
    """Convert stock code to Eastmoney secid format (1.600519 or 0.000001)"""
    code = code.strip().zfill(6)
    return f"1.{code}" if code.startswith("6") else f"0.{code}"


def _push2_headers():
    return {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/", "Origin": "https://quote.eastmoney.com"}


def _datacenter_query(report_name: str, columns: str = "ALL",
                       filter_str: str = "", page_size: int = 50,
                       sort_columns: str = "", sort_types: str = "-1") -> list:
    """Eastmoney datacenter unified query"""
    params = {
        "reportName": report_name, "columns": columns,
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    try:
        r = requests.get(DATACENTER_URL, params=params, headers={"User-Agent": UA}, timeout=15)
        d = r.json()
        if d.get("result") and d["result"].get("data"):
            return d["result"]["data"]
    except Exception:
        pass
    return []


# ===== Fund Flow (P0) =====

def fund_flow_minute(code: str) -> list:
    """Minute-level fund flow (main/large/medium/small/super orders)
    Returns: [{time, main_net, small_net, mid_net, large_net, super_net}]
    Unit: yuan
    """
    url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    params = {
        "secid": _secid(code), "klt": 1,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
    }
    try:
        r = requests.get(url, params=params, headers=_push2_headers(), timeout=10)
        d = r.json()
    except Exception:
        return []
    rows = []
    for line in d.get("data", {}).get("klines", []):
        parts = line.split(",")
        if len(parts) >= 6:
            rows.append({
                "time": parts[0],
                "main_net": float(parts[1]),
                "small_net": float(parts[2]),
                "mid_net": float(parts[3]),
                "large_net": float(parts[4]),
                "super_net": float(parts[5]),
            })
    return rows


def fund_flow_daily(code: str, days: int = 120) -> list:
    """Daily fund flow (main/large/medium/small orders, last N days)
    Returns: [{date, main_net, small_net, mid_net, large_net, super_net}]
    """
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        "secid": _secid(code),
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "lmt": str(days),
    }
    try:
        r = requests.get(url, params=params, headers=_push2_headers(), timeout=15)
        d = r.json()
    except Exception:
        return []
    rows = []
    for line in d.get("data", {}).get("klines", []):
        parts = line.split(",")
        if len(parts) >= 7:
            rows.append({
                "date": parts[0],
                "main_net": float(parts[1]) if parts[1] != "-" else 0,
                "small_net": float(parts[2]) if parts[2] != "-" else 0,
                "mid_net": float(parts[3]) if parts[3] != "-" else 0,
                "large_net": float(parts[4]) if parts[4] != "-" else 0,
                "super_net": float(parts[5]) if parts[5] != "-" else 0,
            })
    return rows


# ===== Dragon Tiger Board (P1) =====

def dragon_tiger_board(code: str = "", start_date: str = "", end_date: str = "",
                        page_size: int = 50) -> list:
    """Dragon Tiger Board (龙虎榜) - institutional seat tracking
    If code given, filter by stock. Otherwise return all recent entries.
    Returns: [{code, name, date, reason, buy_seats, sell_seats, net_buy}]
    """
    filter_parts = []
    if code:
        filter_parts.append(f'(SECURITY_CODE="{code}")')
    if start_date:
        filter_parts.append(f'(TRADE_DATE>=\'{start_date}\')')
    if end_date:
        filter_parts.append(f'(TRADE_DATE<=\'{end_date}\')')
    filter_str = "".join(filter_parts)

    data = _datacenter_query(
        report_name="RPT_DAILYBILLBOARD_DETAILSNEW",
        columns="ALL",
        filter_str=filter_str,
        page_size=page_size,
        sort_columns="TRADE_DATE",
        sort_types="-1",
    )
    results = []
    for item in data:
        results.append({
            "code": item.get("SECURITY_CODE", ""),
            "name": item.get("SECURITY_NAME_ABBR", ""),
            "date": str(item.get("TRADE_DATE", ""))[:10],
            "reason": item.get("EXPLANATION", item.get("EXPLAIN", "")),
            "buy_total": item.get("BILLBOARD_BUY_AMT", 0),
            "sell_total": item.get("BILLBOARD_SELL_AMT", 0),
            "net_buy": item.get("BILLBOARD_NET_AMT", 0),
            "change_pct": item.get("CHANGE_RATE", 0),
            "turnover": item.get("TURNOVERRATE", 0),
        })
    return results


# ===== Margin Trading (P1) =====

def margin_trading(code: str, days: int = 30) -> list:
    """Margin trading details (融资融券)
    Returns: [{date, rz_balance(融资余额), rz_buy(融资买入), rz_repay(融资偿还),
               rq_balance(融券余额), rq_sell(融券卖出)}]
    """
    secid = _secid(code)
    data = _datacenter_query(
        report_name="RPTA_WEB_RZRQ_GGMX",
        columns="DATE,RZYE,RZRQYE,RZMRE,RZCHE,RQYE,RQMCL,RQCHL,RQYL",
        filter_str=f'(SCODE="{code}")',
        page_size=days,
        sort_columns="DATE",
        sort_types="-1",
    )
    results = []
    for item in data:
        results.append({
            "date": str(item.get("DATE", ""))[:10],
            "rz_balance": item.get("RZYE", 0),
            "rz_buy": item.get("RZMRE", 0),
            "rz_repay": item.get("RZCHE", 0),
            "rq_balance": item.get("RQYE", 0),
            "rq_sell": item.get("RQMCL", 0),
        })
    return results


# ===== Research Reports (P1) =====

def research_reports(code: str, page_size: int = 20) -> list:
    """Research reports from Eastmoney (研报)
    Returns: [{title, org, author, date, rating, eps_current, eps_next, pe_current, pe_next}]
    """
    market_code = 1 if code.startswith("6") else 0
    url = "https://reportapi.eastmoney.com/report/list"
    params = {
        "industryCode": "*",
        "pageSize": str(page_size),
        "industry": "*",
        "rating": "*",
        "ratingChange": "*",
        "beginTime": "",
        "endTime": "",
        "pageNo": "1",
        "fields": "",
        "qType": "0",
        "orgCode": "",
        "code": code,
        "rcode": "",
        "p": "1",
        "pageNum": "1",
        "pageNumber": "1",
    }
    try:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=15)
        d = r.json()
    except Exception:
        return []
    results = []
    for item in d.get("data", []):
        results.append({
            "title": item.get("title", ""),
            "org": item.get("orgSName", ""),
            "author": item.get("researcher", ""),
            "date": str(item.get("publishDate", ""))[:10],
            "rating": item.get("emRatingName", ""),
            "eps_current": item.get("predictThisYearEps", 0),
            "eps_next": item.get("predictNextYearEps", 0),
            "pe_current": item.get("predictThisYearPe", 0),
            "pe_next": item.get("predictNextYearPe", 0),
            "industry": item.get("indvInduName", ""),
        })
    return results


# ===== Industry Comparison (P1) =====

def industry_comparison(top_n: int = 20) -> dict:
    """Industry sector ranking by performance (行业板块涨跌排名)
    Returns: {top: [...], bottom: [...], total: int}
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "100", "po": "1", "np": "1",
        "fltt": "2", "invt": "2",
        "fs": "m:90+t:2",
        "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
    }
    try:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=15)
        d = r.json()
        items = d.get("data", {}).get("diff", [])
    except Exception:
        return {"top": [], "bottom": [], "total": 0}

    rows = []
    for i, item in enumerate(items):
        rows.append({
            "rank": i + 1,
            "name": item.get("f14", ""),
            "change_pct": item.get("f3", 0),
            "code": item.get("f12", ""),
            "up_count": item.get("f104", 0),
            "down_count": item.get("f105", 0),
            "leader": item.get("f140", ""),
            "leader_change": item.get("f136", 0),
        })
    return {"top": rows[:top_n], "bottom": rows[-top_n:], "total": len(rows)}


# ===== Block Trade (P1) =====

def block_trade(code: str = "", days: int = 30) -> list:
    """Block trades (大宗交易)
    Returns: [{date, code, name, price, volume, amount, premium, buyer, seller}]
    """
    filter_parts = []
    if code:
        filter_parts.append(f'(SECURITY_CODE="{code}")')
    filter_str = "".join(filter_parts)

    data = _datacenter_query(
        report_name="RPT_BLOCKTRADE_DET_DETAILS",
        columns="ALL",
        filter_str=filter_str,
        page_size=days,
        sort_columns="TRADE_DATE",
        sort_types="-1",
    )
    results = []
    for item in data:
        results.append({
            "date": str(item.get("TRADE_DATE", ""))[:10],
            "code": item.get("SECURITY_CODE", ""),
            "name": item.get("SECURITY_NAME_ABBR", ""),
            "price": item.get("DEAL_PRICE", 0),
            "volume": item.get("DEAL_VOLUME", 0),
            "amount": item.get("DEAL_AMOUNT", 0),
            "premium": item.get("PREMIUM_RATIO", 0),
            "buyer": item.get("BUYER_NAME", ""),
            "seller": item.get("SELLER_NAME", ""),
        })
    return results
