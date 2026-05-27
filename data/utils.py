import re


def parse_code(code: str) -> dict:
    code = code.strip().lower()
    if re.match(r'^(sh|sz|bj)\d{6}$', code):
        market = code[:2]
        bare = code[2:]
        return {"code": bare, "market": market, "full": code}
    if re.match(r'^\d{6}$', code):
        if code.startswith(("6", "5", "9")):
            market = "sh"
        elif code.startswith(("0", "3", "1")):
            market = "sz"
        elif code.startswith(("8", "4")):
            market = "bj"
        else:
            market = "sh"
        return {"code": code, "market": market, "full": market + code}
    return {"code": code, "market": "", "full": code}
