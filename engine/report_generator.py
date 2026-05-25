from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime


class ReportGenerator:
    """报告生成器 - 支持 HTML/CSV/JSON 多格式导出"""

    def generate_html_report(self,
                             result: dict,
                             title: str = "量化回测报告",
                             show_chart: bool = True) -> str:
        """生成 HTML 格式回测报告（内联图表）"""
        metrics = result.get("metrics", {})
        trade_metrics = result.get("trade_metrics", {})
        equity = result.get("equity_curve", [])
        drawdown = result.get("drawdown_curve", [])
        trades = result.get("trades", [])

        final_capital = result.get("final_capital", 0)
        total_return = result.get("total_return", "0%")

        # 构建指标卡片
        metrics_html = ""
        metric_names = ["初始资金", "期末资金", "总收益率", "年化收益率",
                       "夏普比率", "最大回撤", "交易天数"]
        metric_values = [
            f"{result.get('initial_capital', 0):,.2f}",
            f"{final_capital:,.2f}",
            total_return,
            metrics.get("年化收益率", "N/A"),
            metrics.get("夏普比率", "N/A"),
            metrics.get("最大回撤", "N/A"),
            metrics.get("交易天数", "N/A"),
        ]
        for name, val in zip(metric_names, metric_values):
            card_class = "warning" if "最大回撤" in name else "info"
            metrics_html += f"""
            <div class="metric-card {card_class}">
                <div class="metric-label">{name}</div>
                <div class="metric-value">{val}</div>
            </div>"""

        # 交易统计卡片
        trade_card_html = ""
        trade_names = ["盈利次数", "亏损次数", "胜率", "盈亏比", "利润因子"]
        trade_vals = [
            trade_metrics.get("盈利次数", 0),
            trade_metrics.get("亏损次数", 0),
            trade_metrics.get("胜率", "N/A"),
            trade_metrics.get("盈亏比", "N/A"),
            trade_metrics.get("利润因子", "N/A"),
        ]
        for name, val in zip(trade_names, trade_vals):
            trade_card_html += f"""
            <div class="metric-card info">
                <div class="metric-label">{name}</div>
                <div class="metric-value">{val}</div>
            </div>"""

        # 交易明细表格
        trades_html = ""
        if trades:
            trades_html = """
            <h2>交易明细</h2>
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>操作</th>
                        <th>价格</th>
                        <th>数量</th>
                        <th>收益</th>
                    </tr>
                </thead>
                <tbody>"""
            for trade in trades[:50]:
                action_text = "买入" if trade.get("action") == "buy" else "卖出"
                pnl = trade.get("pnl", 0)
                pnl_color = "green" if pnl > 0 else "red"
                trades_html += f"""
                <tr>
                    <td>{trade.get('date', '')}</td>
                    <td>{action_text}</td>
                    <td>{trade.get('price', 0):.2f}</td>
                    <td>{trade.get('shares', 0):.0f}</td>
                    <td style="color:{pnl_color}">{pnl:,.2f}</td>
                </tr>"""
            trades_html += "</tbody></table>"

        if show_chart and equity:
            chart_html = f"""
            <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
            <h2>资金曲线</h2>
            <div id="chart"></div>
            <script>
            var data = {equity};
            var dates = data.map(function(d) {{ return d.date; }});
            var values = data.map(function(d) {{ return d.value; }});
            var trace = {{
                x: dates,
                y: values,
                type: 'scatter',
                mode: 'lines',
                name: '资金曲线',
                line: {{ color: '#1f77b4', width: 2 }}
            }};
            var layout = {{
                title: '回测资金曲线',
                xaxis: {{ title: '日期' }},
                yaxis: {{ title: '资金', rangemode: 'tozero' }},
                height: 400
            }};
            Plotly.newPlot('chart', [trace], layout, {{ responsive: true }});
            </script>"""
        else:
            chart_html = ""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f6fa;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 15px; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; margin-top: 30px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric-card {{
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-card.info {{ background: #ffffff; border-left: 4px solid #3498db; }}
        .metric-card.warning {{ background: #fff5f5; border-left: 4px solid #e74c3c; }}
        .metric-card.success {{ background: #f0fff4; border-left: 4px solid #27ae60; }}
        .metric-label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        th {{
            background: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .footer {{
            text-align: center;
            color: #95a5a6;
            margin-top: 40px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {title}</h1>
        <p>报告日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="metrics-grid">
            {metrics_html}
        </div>
        <div class="metrics-grid">
            {trade_card_html}
        </div>
        {chart_html}
        {trades_html}
        <div class="footer">
            <p>量化选股回测平台 | 自动生成报告</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def generate_csv(self,
                     result: dict,
                     filename: str = "backtest_trades.csv") -> str:
        """生成 CSV 交易记录报告"""
        trades = result.get("trades", [])
        if not trades:
            df = pd.DataFrame(columns=["date", "action", "price", "shares", "pnl"])
        else:
            df = pd.DataFrame(trades)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        return filename

    def generate_json(self,
                      result: dict,
                      filename: str = "backtest_report.json") -> str:
        """生成 JSON 格式报告"""
        import json
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "platform": "量化选股回测平台",
                "version": "2.0.0"
            },
            "metrics": result.get("metrics", {}),
            "equity_curve": result.get("equity_curve", []),
            "drawdown_curve": result.get("drawdown_curve", []),
            "final_capital": result.get("final_capital", 0),
            "total_return": result.get("total_return", "0%"),
            "trade_count": len(result.get("trades", [])),
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filename

    def export_all(self,
                   result: dict,
                   base_name: str = "report") -> dict:
        """一键生成所有格式报告"""
        reports = {}
        try:
            html = self.generate_html_report(result, "量化回测报告")
            html_path = f"{base_name}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            reports["html"] = html_path
        except Exception as e:
            reports["html"] = f"Error: {e}"

        try:
            csv_path = self.generate_csv(result, f"{base_name}_trades.csv")
            reports["csv"] = csv_path
        except Exception as e:
            reports["csv"] = f"Error: {e}"

        try:
            json_path = self.generate_json(result, f"{base_name}_data.json")
            reports["json"] = json_path
        except Exception as e:
            reports["json"] = f"Error: {e}"

        return reports
