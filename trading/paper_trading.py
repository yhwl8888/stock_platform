from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass
class PaperPosition:
    code: str
    name: str = ""
    shares: int = 0
    cost: float = 0.0
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost_total(self) -> float:
        return self.shares * self.cost

    @property
    def pnl(self) -> float:
        return self.market_value - self.cost_total

    @property
    def pnl_pct(self) -> float:
        if self.cost == 0:
            return 0.0
        return (self.current_price / self.cost - 1) * 100


@dataclass
class PaperOrder:
    code: str
    action: str  # buy / sell
    price: float
    shares: int
    amount: float
    status: str = "pending"  # pending / filled / cancelled
    created_at: str = ""
    filled_at: str = ""
    order_id: str = ""


class PaperTrading:
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, PaperPosition] = {}
        self.orders: list[PaperOrder] = []
        self.order_counter = 0
        self.history: list[dict] = []
        self._init_capital_log = initial_capital

    @property
    def total_assets(self) -> float:
        pos_value = sum(p.market_value for p in self.positions.values())
        return self.cash + pos_value

    @property
    def total_pnl(self) -> float:
        return self.total_assets - self.initial_capital

    @property
    def total_pnl_pct(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return (self.total_assets / self.initial_capital - 1) * 100

    def place_order(self, code: str, action: str, price: float, shares: int) -> PaperOrder:
        self.order_counter += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order = PaperOrder(
            code=code,
            action=action,
            price=price,
            shares=shares,
            amount=price * shares,
            status="pending",
            created_at=now,
            order_id=f"ORD{self.order_counter:06d}",
        )

        if action == "buy":
            needed = order.amount * 1.00025
            if needed <= self.cash and shares >= 100:
                self.cash -= needed
                if code in self.positions:
                    pos = self.positions[code]
                    total_cost = pos.cost_total + order.amount
                    total_shares = pos.shares + shares
                    pos.cost = total_cost / total_shares
                    pos.shares = total_shares
                else:
                    self.positions[code] = PaperPosition(
                        code=code, shares=shares, cost=price
                    )
                order.status = "filled"
                order.filled_at = now
            else:
                order.status = "cancelled"

        elif action == "sell":
            pos = self.positions.get(code)
            if pos and pos.shares >= shares:
                proceeds = order.amount * 0.999
                self.cash += proceeds
                pos.shares -= shares
                if pos.shares == 0:
                    del self.positions[code]
                order.status = "filled"
                order.filled_at = now
            else:
                order.status = "cancelled"

        self.orders.append(order)
        self.history.append({
            "时间": order.created_at,
            "订单号": order.order_id,
            "代码": code,
            "方向": "买入" if action == "buy" else "卖出",
            "价格": price,
            "数量": shares,
            "金额": order.amount,
            "状态": "已成交" if order.status == "filled" else ("待成交" if order.status == "pending" else "已撤销"),
        })
        return order

    def update_prices(self, prices: dict[str, float]):
        for code, price in prices.items():
            if code in self.positions:
                self.positions[code].current_price = price

    def get_positions_df(self) -> pd.DataFrame:
        if not self.positions:
            return pd.DataFrame()
        rows = []
        for code, pos in self.positions.items():
            rows.append({
                "代码": code,
                "名称": pos.name,
                "持仓数量": pos.shares,
                "成本价": round(pos.cost, 2),
                "现价": round(pos.current_price, 2),
                "市值": round(pos.market_value, 2),
                "盈亏": round(pos.pnl, 2),
                "盈亏比": f"{pos.pnl_pct:.2f}%",
            })
        return pd.DataFrame(rows)

    def get_history_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.history) if self.history else pd.DataFrame()

    def reset(self):
        self.cash = self.initial_capital
        self.positions.clear()
        self.orders.clear()
        self.history.clear()
        self.order_counter = 0
