import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"

DB_PATH = STORAGE_DIR / "stock_data.db"
os.makedirs(STORAGE_DIR, exist_ok=True)

CACHE_EXPIRE_HOURS = 4

DEFAULT_START_DATE = "20200101"
DEFAULT_END_DATE = "20251231"

TRADING_FEE_RATE = 0.00025
MIN_TRADING_FEE = 5.0
STAMP_TAX_RATE = 0.001

INITIAL_CAPITAL = 1000000.0
