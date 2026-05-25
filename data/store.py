import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Iterable

import pandas as pd

from config.settings import DB_PATH, CACHE_EXPIRE_HOURS


def _chunked_insert(pd_table, conn, keys, data_iter):
    data = list(data_iter)
    batch_size = 400
    for i in range(0, len(data), batch_size):
        chunk = data[i:i + batch_size]
        conn.executemany(
            f"INSERT OR IGNORE INTO {pd_table.name} ({','.join(keys)}) "
            f"VALUES ({','.join(['?'] * len(keys))})",
            chunk
        )
    conn.connection.commit()


class DataStore:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_price (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                PRIMARY KEY (code, date)
            );
            CREATE TABLE IF NOT EXISTS stock_basic (
                code TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                market TEXT,
                list_date TEXT,
                last_update TEXT
            );
            CREATE TABLE IF NOT EXISTS index_daily (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (code, date)
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold REAL NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, condition)
            );
            CREATE INDEX IF NOT EXISTS idx_daily_code ON daily_price(code);
            CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_price(date);
            CREATE INDEX IF NOT EXISTS idx_index_code ON index_daily(code);
            CREATE INDEX IF NOT EXISTS idx_watchlist_code ON watchlist(code);
            CREATE INDEX IF NOT EXISTS idx_alerts_code ON price_alerts(code);
        """)
        self.conn.commit()

    def save_daily(self, df: pd.DataFrame, code: str):
        if df is None or df.empty:
            return
        df = df.copy()
        df["code"] = code
        if {"开盘", "收盘"}.issubset(df.columns):
            df = df.rename(columns={
                "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low",
                "成交量": "volume", "成交额": "amount"
            })
        cols = {"open", "close", "high", "low", "volume", "amount"}
        if not cols.issubset(df.columns):
            return
        df = df[["code", "date", "open", "high", "low", "close", "volume", "amount"]].copy()
        df = df.dropna(subset=["date"])
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
        df.to_sql("daily_price", self.conn, if_exists="append", index=False, method=_chunked_insert)

    def get_daily(self, code: str, start: str = None, end: str = None) -> pd.DataFrame:
        query = "SELECT * FROM daily_price WHERE code = ?"
        params = [code]
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date"
        df = pd.read_sql(query, self.conn, params=params)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        return df

    def get_cached_daily(self, code: str, latest_date: str) -> bool:
        res = self.conn.execute(
            "SELECT COUNT(*) FROM daily_price WHERE code = ? AND date = ?",
            (code, latest_date)
        ).fetchone()
        return res[0] > 0

    def save_basic(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        df = df.copy()
        df["last_update"] = datetime.now().strftime("%Y-%m-%d")
        df.to_sql("stock_basic", self.conn, if_exists="replace", index=False, method=_chunked_insert)

    def get_basic(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM stock_basic ORDER BY code", self.conn)

    def search_stocks(self, keyword: str) -> pd.DataFrame:
        kw = keyword.strip()
        if not kw:
            return self.get_basic()
        try:
            return pd.read_sql(
                "SELECT * FROM stock_basic WHERE code LIKE ? OR name LIKE ? ORDER BY code",
                self.conn, params=(f"%{kw}%", f"%{kw}%")
            )
        except Exception:
            return self.get_basic()

    def add_watchlist(self, code: str, name: str = "") -> bool:
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO watchlist (code, name) VALUES (?, ?)",
                (code, name)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def remove_watchlist(self, code: str) -> bool:
        try:
            self.conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_watchlist(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM watchlist ORDER BY added_at DESC", self.conn)

    def is_in_watchlist(self, code: str) -> bool:
        res = self.conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE code = ?", (code,)
        ).fetchone()
        return res[0] > 0

    def add_price_alert(self, code: str, condition: str, threshold: float, enabled: bool = True) -> bool:
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO price_alerts (code, condition, threshold, enabled) VALUES (?, ?, ?, ?)",
                (code, condition, threshold, 1 if enabled else 0)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def remove_price_alert(self, code: str, condition: str) -> bool:
        try:
            self.conn.execute(
                "DELETE FROM price_alerts WHERE code = ? AND condition = ?",
                (code, condition)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_price_alerts(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM price_alerts ORDER BY code", self.conn)

    def close(self):
        self.conn.close()
