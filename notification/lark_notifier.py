import subprocess
import json
from datetime import datetime


class LarkNotifier:
    def __init__(self):
        self.enabled = False
        self.user_id = None
        self._check_and_configure()
    
    def _check_and_configure(self):
        try:
            result = subprocess.run(
                "lark-cli auth status",
                capture_output=True,
                text=True,
                timeout=10,
                shell=True
            )
            data = json.loads(result.stdout)
            if data.get("identity") == "user" and data.get("tokenStatus") == "valid":
                self.enabled = True
                self.user_id = data.get("userOpenId")
        except Exception:
            pass
    
    def send_message(self, chat_id: str = None, user_id: str = None, 
                     content: str = "") -> bool:
        if not self.enabled:
            return False
        
        cmd = 'lark-cli im +messages-send'
        
        if chat_id:
            cmd += f' --chat-id {chat_id}'
        elif user_id:
            cmd += f' --user-id {user_id}'
        elif self.user_id:
            cmd += f' --user-id {self.user_id}'
        else:
            return False
        
        cmd += f' --text "{content}"'
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
            data = json.loads(result.stdout)
            return data.get("ok", False)
        except Exception:
            return False
    
    def send_price_alert(self, code: str, name: str, price: float, 
                        change_pct: float, condition: str, threshold: float) -> bool:
        condition_map = {
            "above": "高于",
            "below": "低于",
            "rise_pct": "涨幅大于",
            "fall_pct": "跌幅大于"
        }
        condition_text = condition_map.get(condition, condition)
        
        message = f"""[价格预警] {code} {name}
当前价: {price:.2f}
涨跌幅: {change_pct:+.2f}%
条件: {condition_text} {threshold:.2f}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send_message(content=message)
    
    def send_backtest_result(self, strategy_name: str, final_capital: float,
                            total_return: float, sharpe: float, max_drawdown: float) -> bool:
        return_emoji = "+" if total_return > 0 else ""
        
        message = f"""[回测完成] {strategy_name}
最终资产: {final_capital:,.2f}
总收益率: {return_emoji}{total_return:.2f}%
夏普比率: {sharpe:.2f}
最大回撤: {max_drawdown:.2f}%
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send_message(content=message)
    
    def send_trade_notification(self, code: str, name: str, action: str,
                                price: float, shares: int, amount: float) -> bool:
        action_emoji = "买入" if action == "buy" else "卖出"
        
        message = f"""[交易通知] {code} {name}
操作: {action_emoji}
价格: {price:.2f}
数量: {shares}股
金额: {amount:,.2f}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send_message(content=message)
    
    def send_watchlist_update(self, code: str, name: str, price: float,
                             change_pct: float, reason: str = "") -> bool:
        change_emoji = "+" if change_pct > 0 else ""
        
        message = f"""[自选股动态] {code} {name}
当前价: {price:.2f}
涨跌幅: {change_emoji}{change_pct:.2f}%
{reason}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send_message(content=message)
    
    def is_enabled(self) -> bool:
        return self.enabled


notifier = LarkNotifier()