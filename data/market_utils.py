# -*- coding: utf-8 -*-
"""Market code utilities - disambiguate stock vs index codes"""
import re

INDEX_CODES = {
    "000001": {"name": "Shanghai Composite", "market": "sh", "full": "sh000001"},
    "399001": {"name": "Shenzhen Component", "market": "sz", "full": "sz399001"},
    "399006": {"name": "ChiNext Index", "market": "sz", "full": "sz399006"},
    "399005": {"name": "SME Index", "market": "sz", "full": "sz399005"},
    "000300": {"name": "CSI 300", "market": "sh", "full": "sh000300"},
    "000016": {"name": "SSE 50", "market": "sh", "full": "sh000016"},
    "000010": {"name": "SSE 180", "market": "sh", "full": "sh000010"},
    "000905": {"name": "CSI 500", "market": "sh", "full": "sh000905"},
    "000852": {"name": "CSI 1000", "market": "sh", "full": "sh000852"},
}

AMBIGUOUS_STOCKS = {
    "000001": {"name": "Ping An Bank", "market": "sz", "full": "sz000001"},
}


def parse_code(code):
    """Parse a code string into structured info.
    Accepts formats:
      - 'sh000001' -> index (Shanghai Composite)
      - 'sz000001' -> stock (Ping An Bank)
      - '000001'   -> ambiguous, returns both possibilities
      - '600519'   -> stock, auto-detect market
    """
    code = code.strip().lower()
    # Already prefixed
    if re.match(r'^(sh|sz|bj)\d{6}$', code):
        market = code[:2]
        bare = code[2:]
        is_index = bare in INDEX_CODES and market == INDEX_CODES[bare]["market"]
        if is_index:
            info = INDEX_CODES[bare]
            return {"code": bare, "name": info["name"], "market": market,
                    "full_code": code, "type": "index"}
        return {"code": bare, "name": "", "market": market,
                "full_code": code, "type": "stock"}
    # Bare 6-digit code
    if re.match(r'^\d{6}$', code):
        if code in INDEX_CODES:
            info = INDEX_CODES[code]
            if code in AMBIGUOUS_STOCKS:
                stock_info = AMBIGUOUS_STOCKS[code]
                return {
                    "code": code, "ambiguous": True,
                    "index": {"name": info["name"], "market": info["market"],
                              "full_code": info["full"], "type": "index"},
                    "stock": {"name": stock_info["name"], "market": stock_info["market"],
                              "full_code": stock_info["full"], "type": "stock"},
                }
            return {"code": code, "name": info["name"], "market": info["market"],
                    "full_code": info["full"], "type": "index"}
        # Auto-detect market for stocks
        if code.startswith("6") or code.startswith("5") or code.startswith("9"):
            market = "sh"
        elif code.startswith("0") or code.startswith("3") or code.startswith("1"):
            market = "sz"
        elif code.startswith("8") or code.startswith("4"):
            market = "bj"
        else:
            market = "sh"
        return {"code": code, "name": "", "market": market,
                "full_code": market + code, "type": "stock"}
    return {"code": code, "name": "", "market": "", "full_code": code, "type": "unknown"}


def is_index(code):
    """Check if a code refers to an index"""
    parsed = parse_code(code)
    if parsed.get("ambiguous"):
        return False
    return parsed.get("type") == "index"


def get_full_code(code):
    """Get full code with market prefix (e.g., sh000001, sz600519)"""
    parsed = parse_code(code)
    if parsed.get("ambiguous"):
        return parsed["stock"]["full_code"]  # default to stock
    return parsed.get("full_code", code)


def get_market(code):
    """Get market prefix (sh/sz/bj)"""
    parsed = parse_code(code)
    if parsed.get("ambiguous"):
        return "sz"
    return parsed.get("market", "")


def disambiguate(code, prefer="stock"):
    """Disambiguate an ambiguous code. prefer: 'stock' or 'index'"""
    parsed = parse_code(code)
    if parsed.get("ambiguous"):
        return parsed.get(prefer, parsed["stock"])
    return parsed
