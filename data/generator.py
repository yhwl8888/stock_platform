import numpy as np
import pandas as pd
from datetime import datetime, timedelta


REALISTIC_PRICES = {
    "600519": 1580, "000858": 135, "002304": 110, "000568": 140,
    "600809": 200, "600276": 42, "600436": 220, "300750": 200,
    "002594": 280, "300760": 280, "002415": 32, "002475": 36,
    "000333": 68, "000651": 42, "000725": 4.5, "600036": 38,
    "601318": 55, "600030": 22, "601166": 20, "601398": 7,
    "600887": 28, "600900": 30, "600585": 28, "601088": 42,
    "601857": 10, "002714": 48, "002352": 42, "002230": 48,
    "002371": 350, "002920": 100, "300059": 18, "300124": 65,
    "300015": 14, "300033": 175, "300274": 80, "300308": 120,
    "300413": 22, "300433": 20, "300498": 18, "300502": 100,
    "300782": 80, "600690": 28, "600941": 110, "601127": 100,
    "601899": 18, "688041": 100, "688111": 280, "688256": 150,
    "688981": 70, "002007": 18, "002270": 18,
}


def generate_stock_data(code: str, name: str = "",
                        start: str = "20200101", end: str = "20251231",
                        base_price: float = None) -> pd.DataFrame:
    start_dt = datetime.strptime(start, "%Y%m%d") if len(start) == 8 else datetime.strptime(start.replace("-", ""), "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d") if len(end) == 8 else datetime.strptime(end.replace("-", ""), "%Y%m%d")

    if base_price is None:
        code_num = code.strip().zfill(6)
        first_char = code_num[0]
        try:
            base_price = REALISTIC_PRICES.get(code, {3: 20, 6: 60, 0: 15, 2: 8, 8: 15}.get(int(first_char), 10) * 10)
        except ValueError:
            base_price = 20.0

    dates = pd.bdate_range(start_dt, end_dt)
    if len(dates) < 20:
        return pd.DataFrame()

    n = len(dates)
    try:
        np.random.seed(int(code.strip().zfill(6)))
    except ValueError:
        np.random.seed(hash(code) % 10000)

    raw = np.cumsum(np.random.randn(n) * 0.012)
    raw = raw - np.linspace(raw[0], raw[-1], n)
    max_dev = np.max(np.abs(raw))
    if max_dev > 0:
        raw = raw / max_dev * 0.15
    prices = base_price * (1 + raw)
    prices = np.maximum(prices, base_price * 0.5)

    daily_vol = base_price * 0.015
    opens = prices + np.random.randn(n) * daily_vol * 0.5
    highs = np.maximum(opens, prices) + abs(np.random.randn(n) * daily_vol * 0.6)
    lows = np.minimum(opens, prices) - abs(np.random.randn(n) * daily_vol * 0.6)
    closes = prices
    volumes = (np.random.rand(n) * 0.5 + 0.5) * 2000000 * (prices / base_price)
    amounts = volumes * closes

    df = pd.DataFrame({
        "date": dates.strftime("%Y%m%d"),
        "open": np.round(np.maximum(opens, 0.01), 2),
        "high": np.round(np.maximum(highs, 0.01), 2),
        "low": np.round(np.maximum(lows, 0.01), 2),
        "close": np.round(np.maximum(closes, 0.01), 2),
        "volume": np.round(volumes, 0).astype(int),
        "amount": np.round(amounts, 0).astype(int),
    })
    return df


SAMPLE_STOCKS = [
    # 银行证券
    ("000001", "平安银行"), ("000002", "万科A"), ("600000", "浦发银行"),
    ("600015", "华夏银行"), ("600016", "民生银行"), ("600036", "招商银行"),
    ("601009", "南京银行"), ("601166", "兴业银行"), ("601288", "农业银行"),
    ("601328", "交通银行"), ("601398", "工商银行"), ("601939", "建设银行"),
    ("601988", "中国银行"), ("600030", "中信证券"), ("600837", "海通证券"),
    ("601688", "中国银河"), ("000001", "平安银行"),
    
    # 消费
    ("000858", "五粮液"), ("000568", "泸州老窖"), ("000799", "金种子酒"),
    ("600519", "贵州茅台"), ("600809", "山西汾酒"), ("600887", "伊利股份"),
    ("600858", "三星医疗"), ("000333", "美的集团"), ("000651", "格力电器"),
    ("000921", "浙江龙盛"), ("002032", "苏泊尔"), ("002242", "万丰奥特"),
    ("002304", "洋河股份"), ("002329", "皇台酒业"), ("002507", "涪陵榨菜"),
    
    # 科技
    ("000063", "中兴通讯"), ("000725", "京东方A"), ("002230", "科大讯飞"),
    ("002410", "广联达"), ("002415", "海康威视"), ("002444", "巨星科技"),
    ("002475", "立讯精密"), ("002493", "华泰股份"), ("002594", "比亚迪"),
    ("002714", "牧原股份"), ("002920", "德赛西威"), ("300001", "睿创微纳"),
    ("300015", "爱尔眼科"), ("300033", "同花顺"), ("300059", "东方财富"),
    ("300124", "汇川技术"), ("300142", "沃森生物"), ("300212", "易瑞生物"),
    ("300274", "阳光电源"), ("300308", "中际旭创"), ("300413", "芒果超媒"),
    ("300433", "蓝思科技"), ("300498", "温氏股份"), ("300502", "新易盛"),
    ("300750", "宁德时代"), ("300760", "迈瑞医疗"), ("300782", "卓胜微"),
    ("300896", "爱博医疗"), ("301029", "怡和嘉业"),
    
    # 医药
    ("600276", "恒瑞医药"), ("600436", "片仔癀"), ("600518", "康美药业"),
    ("600529", "山东药玻"), ("600535", "天士力"), ("600566", "济川药业"),
    ("600664", "哈药股份"), ("600673", "东阳光"), ("600683", "京华集团"),
    ("002007", "华兰生物"), ("002223", "鱼跃医疗"), ("002252", "莱宝高科"),
    ("002287", "奇安信"), ("002294", "博济医药"), ("002317", "众生药业"),
    ("002349", "精华制药"), ("002370", "安洁科技"), ("002382", "蓝帆医疗"),
    ("002393", "上海莱士"), ("002412", "汉森制药"), ("002422", "科伦药业"),
    ("002458", "立中集团"), ("002511", "中顺洁柔"),
    
    # 制造业
    ("600309", "万华化学"), ("600585", "海螺水泥"), ("600690", "海尔智家"),
    ("600874", "创业环保"), ("600900", "长江电力"), ("600941", "中国移动"),
    ("601088", "中国神华"), ("601601", "中国太保"), ("601628", "中国人寿"),
    ("601857", "中国石油"), ("601899", "紫金矿业"), ("601939", "建设银行"),
    ("601988", "中国银行"), ("601318", "中国平安"),
    ("601127", "赛力斯"), ("601668", "中国建筑"), ("601766", "中国电建"),
    ("601988", "中国银行"), ("688041", "海光信息"), ("688111", "金山办公"),
    ("688256", "寒武纪"), ("688981", "中芯国际"), ("688327", "华大九天"),
    ("688369", "赛腾股份"), ("688408", "恒玄科技"), ("688521", "芯原股份"),
    ("688536", "思瑞浦"), ("688561", "奥比中光"), ("688608", "恒玄科技"),
]


def generate_sample_data(start: str = "20200101", end: str = "20251231",
                         stock_list: list = None) -> dict[str, pd.DataFrame]:
    from data.store import DataStore
    store = DataStore()

    data = {}
    stocks = stock_list or SAMPLE_STOCKS
    basic_records = []

    for code, name in stocks:
        df = generate_stock_data(code, name, start, end)
        if not df.empty:
            store.save_daily(df, code)
            data[code] = store.get_daily(code, start.replace("-", ""), end.replace("-", ""))
        basic_records.append({"code": code, "name": name, "industry": "",
                              "market": "sz" if code.startswith("0") or code.startswith("3") else "sh",
                              "list_date": "20000101", "last_update": datetime.now().strftime("%Y-%m-%d")})

    basic_df = pd.DataFrame(basic_records)
    store.save_basic(basic_df)
    store.close()
    return data


def load_csv_data(filepath: str, code: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    required = {"date", "open", "high", "low", "close", "volume"}
    df.columns = [c.strip().lower() for c in df.columns]
    if not required.issubset(df.columns):
        alt_map = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume"}
        df = df.rename(columns=alt_map)
    if not required.issubset(df.columns):
        raise ValueError(f"CSV必须包含列: {required}")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
    from data.store import DataStore
    store = DataStore()
    store.save_daily(df, code)
    store.close()
    return df
