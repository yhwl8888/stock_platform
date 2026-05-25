import requests
import re
from typing import Optional, Dict, List
import pandas as pd
from datetime import datetime


TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="


def _get_qcode(code: str) -> str:
    """Convert stock/index code to Tencent format. Supports prefixed codes like sh000001, sz000001"""
    code = code.strip().lower()
    # Already prefixed
    if code.startswith(("sh", "sz", "bj")) and len(code) == 8:
        return code
    # Bare code - use market_utils
    bare = code.zfill(6)
    try:
        from data.market_utils import get_full_code
        return get_full_code(bare)
    except ImportError:
        pass
    # Fallback
    if bare.startswith("6") or bare.startswith("5") or bare.startswith("9"):
        return f"sh{bare}"
    elif bare.startswith("0") or bare.startswith("3") or bare.startswith("1"):
        return f"sz{bare}"
    elif bare.startswith("8") or bare.startswith("4"):
        return f"bj{bare}"
    return f"sh{bare}"
    
    # 股票代码判断
    if code.startswith("6") or code.startswith("5") or code.startswith("9"):
        return f"sh{code}"  # 上海主板/科创板
    elif code.startswith("0") or code.startswith("3") or code.startswith("1"):
        return f"sz{code}"  # 深圳主板/创业板
    elif code.startswith("8") or code.startswith("4"):
        return f"bj{code}"  # 北京板
    
    return f"sh{code}"


def fetch_realtime_quotes(codes: List[str], timeout: float = 10.0) -> Dict[str, dict]:
    """批量获取腾讯实时行情
    
    Returns:
        Dict of {code: {"code", "name", "price", "open", "high", "low", "volume", "change_pct", "pre_close", "source"}}
    """
    if not codes:
        return {}
    
    qcodes = [_get_qcode(c) for c in codes]
    url = TENCENT_QUOTE_URL + ",".join(qcodes)
    
    result = {}
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        text = resp.text
        
        for qcode in qcodes:
            key = f"v_{qcode}"
            if key not in text:
                continue
            
            pattern = f'{key}="([^"]+)"'
            match = re.search(pattern, text)
            if not match:
                continue
            
            fields = match.group(1).split("~")
            if len(fields) < 50:
                continue
            
            raw_code = fields[2].strip().zfill(6)
            try:
                price = float(fields[3]) if fields[3] else 0
                pre_close = float(fields[4]) if fields[4] else 0
                open_price = float(fields[5]) if fields[5] else 0
                volume = float(fields[6]) * 100 if fields[6] else 0  # 手转股
                
                change_pct = 0
                if pre_close > 0 and price > 0:
                    change_pct = ((price - pre_close) / pre_close) * 100
                
                high = float(fields[33]) if fields[33] else price
                low = float(fields[34]) if fields[34] else price
                
                if price > 0:
                    result[raw_code] = {
                        "code": raw_code,
                        "name": fields[1].strip(),
                        "price": price,
                        "pre_close": pre_close,
                        "open": open_price,
                        "high": high if high > 0 else price,
                        "low": low if low > 0 else price,
                        "volume": int(volume),
                        "change_pct": round(change_pct, 2),
                        "source": "tencent",
                    }
            except (ValueError, IndexError):
                continue
                
    except Exception as e:
        print(f"腾讯API请求失败: {e}")
    
    return result


def fetch_single_quote(code: str, timeout: float = 5.0) -> Optional[dict]:
    """获取单只股票实时行情"""
    result = fetch_realtime_quotes([code], timeout)
    return result.get(code.strip().zfill(6))


def fetch_historical_kline(code: str, start_date: str = "20200101", 
                           end_date: str = "20251231", adjust: str = "qfq") -> pd.DataFrame:
    """获取历史K线数据 - 腾讯财经接口
    
    注意: 腾讯没有免费的历史K线API，这里使用本地模拟数据
    后续可以考虑使用akshare或者其他源
    """
    return pd.DataFrame()


def check_tencent_network(timeout: float = 3.0) -> bool:
    """检查腾讯API是否可用"""
    try:
        resp = requests.get(f"{TENCENT_QUOTE_URL}sh600519", timeout=timeout)
        return resp.status_code == 200 and "v_sh600519" in resp.text
    except Exception:
        return False