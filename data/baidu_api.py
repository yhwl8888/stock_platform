# -*- coding: utf-8 -*-
"""Baidu Finance API - concept blocks attribution"""
import requests

_BAIDU_PAE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://gushitong.baidu.com/",
}


def concept_blocks(code: str) -> dict:
    """Get concept/industry/region blocks for a stock (百度概念板块归属)
    Returns: {industry: [...], concept: [...], region: [...], concept_tags: [...]}
    """
    url = (
        f"https://finance.pae.baidu.com/api/getrelatedblock"
        f"?code={code}&market=ab"
        f"&typeCode=all&finClientType=pc"
    )
    try:
        r = requests.get(url, headers=_BAIDU_PAE_HEADERS, timeout=10)
        d = r.json()
        if str(d.get("ResultCode", -1)) != "0":
            return {"industry": [], "concept": [], "region": [], "concept_tags": []}
    except Exception:
        return {"industry": [], "concept": [], "region": [], "concept_tags": []}

    result = {"industry": [], "concept": [], "region": [], "concept_tags": []}
    for block in d.get("Result", []):
        block_type = block.get("type", "")
        for item in block.get("list", []):
            entry = {
                "name": item.get("name", ""),
                "change_pct": item.get("increase", ""),
                "desc": item.get("desc", ""),
            }
            if "行业" in block_type:
                result["industry"].append(entry)
            elif "概念" in block_type:
                result["concept"].append(entry)
                result["concept_tags"].append(entry["name"])
            elif "地域" in block_type:
                result["region"].append(entry)
    return result
