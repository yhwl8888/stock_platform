import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

DEFAULT_START = "20240101"
DEFAULT_END = "20261231"

GRID_CONFIG = {
    "起投金额": 10000,
    "回测天数": 60,
    "止损比例": 0.05,
    "止盈比例": 0.10,
}

STRATEGY_OPTIONS = [
    {"id": "ma_crossover", "name": "MA5/MA20 金叉", "desc": "MA5上穿MA20买入，下穿卖出"},
    {"id": "dual_thrust", "name": "Dual Thrust 通道突破", "desc": "基于前N日价格范围设定突破通道"},
    {"id": "heikin_ashi", "name": "Heikin-Ashi 均值K线", "desc": "Heikin-Ashi蜡烛图形态识别"},
    {"id": "parabolic_sar", "name": "Parabolic SAR 抛物线", "desc": "抛物线指标趋势跟踪"},
]
