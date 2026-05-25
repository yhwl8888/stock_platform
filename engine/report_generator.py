from __future__ import annotations
import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime


class ReportGenerator:
    """报告生成器 - 支持 HTML/CSV/JSON 多格式导出"""

    _BASE_CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
    margin: 0; padding: 20px; background: #f5f6fa;
}
.container { max-width: 1200px; margin: 0 auto; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 15px; }
h2 { color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; margin-top: 30px; }
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 15px; margin: 20px 0;
}
.metric-card {
    padding: 20px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;
}
.metric-card.info { background: #ffffff; border-left: 4px solid #3498db; }
.metric-card.warning { background: #fff5f5; border-left: 4px solid #e74c3c; }
.metric-card.success { background: #f0fff4; border-left: 4px solid #27ae60; }
.metric-label { font-size: 14px; color: #7f8c8d; margin-bottom: 8px; }
.metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
table {
    width: 100%; border-collapse: collapse; background: #fff;
    border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
th { background: #34495e; color: white; padding: 12px; text-align: left; }
td { padding: 10px 12px; border-bottom: 1px solid #ecf0f1; }
tr:hover { background: #f8f9fa; }
.footer { text-align: center; color: #95a5a6; margin-top: 40px; padding: 20px; }
.highlight-best { background: #e8f8f5 !important; font-weight: bold; }
.chart-section { margin: 25px 0; }
.risk-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px; margin: 15px 0;
}
.risk-card {
    padding: 15px; border-radius: 6px;
    background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.risk-card .label { font-size: 13px; color: #95a5a6; }
.risk-card .value { font-size: 20px; font-weight: bold; color: #2c3e50; }
@media (max-width: 768px) {
    body { padding: 10px; }
    .container { padding: 0 5px; }
    .metrics-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
    .metric-card { padding: 12px; }
    .metric-value { font-size: 18px; }
    .metric-label { font-size: 12px; }
    table { font-size: 13px; }
    th, td { padding: 8px 6px; }
    h1 { font-size: 20px; }
    h2 { font-size: 16px; }
}
@media (max-width: 480px) {
    .metrics-grid { grid-template-columns: 1fr; }
    .metric-value { font-size: 16px; }
}"""

    def generate_monthly_returns(self, equity_curve: pd.Series) -> pd.DataFrame:
        if equity_curve.empty or len(equity_curve) < 2:
            return pd.DataFrame()
        if not isinstance(equity_curve.index, pd.DatetimeIndex):
            equity_curve = equity_curve.copy()
            equity_curve.index = pd.to_datetime(equity_curve.index)
        monthly = equity_curve.resample("ME").last()
        monthly_returns = monthly.pct_change().dropna()
        if monthly_returns.empty:
            return pd.DataFrame()
        df = pd.DataFrame({
            "year": monthly_returns.index.year,
            "month": monthly_returns.index.month,
            "return": monthly_returns.values,
        })
        pivot = df.pivot_table(index="year", columns="month", values="return", aggfunc="first")
        pivot.columns = [f"{m}月" for m in pivot.columns]
        return pivot

    def _monthly_heatmap_html(self, equity_curve: list) -> str:
        if not equity_curve:
            return ""
        try:
            ec = pd.Series(
                [d["value"] for d in equity_curve],
                index=pd.to_datetime([d["date"] for d in equity_curve]),
            )
            pivot = self.generate_monthly_returns(ec)
            if pivot.empty:
                return ""
        except Exception:
            return ""
        rows = ""
        for year in sorted(pivot.index):
            cells = '<td style="font-weight:bold;background:#34495e;color:#fff;padding:8px;">' + str(year) + '</td>'
            for m in range(1, 13):
                col = str(m) + "月"
                val = pivot.loc[year, col] if col in pivot.columns else None
                if pd.isna(val):
                    cells += '<td style="padding:8px;background:#f0f0f0;">-</td>'
                else:
                    pct = float(val)
                    if pct > 0:
                        intensity = min(abs(pct) * 5, 1)
                        bg = "rgba(39,174,96," + str(0.15 + intensity * 0.55) + ")"
                    elif pct < 0:
                        intensity = min(abs(pct) * 5, 1)
                        bg = "rgba(231,76,60," + str(0.15 + intensity * 0.55) + ")"
                    else:
                        bg = "#f9f9f9"
                    cells += '<td style="padding:8px;text-align:center;background:' + bg + ';">' + f"{pct:.2%}" + "</td>"
            rows += "<tr>" + cells + "</tr>"
        header_cells = "<th>年份</th>" + "".join("<th>" + str(m) + "月</th>" for m in range(1, 13))
        return """
        <h2>月度收益率热力图</h2>
        <div style="overflow-x:auto;">
        <table style="min-width:700px;">
            <thead><tr>""" + header_cells + """</tr></thead>
            <tbody>""" + rows + """</tbody>
        </table>
        </div>"""

    def _trade_pie_html(self, trades: list) -> str:
        if not trades:
            return ""
        sell_trades = [t for t in trades if t.get("action") == "sell"]
        if not sell_trades:
            return ""
        wins = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
        losses = sum(1 for t in sell_trades if t.get("pnl", 0) < 0)
        breakeven = len(sell_trades) - wins - losses
        if wins + losses + breakeven == 0:
            return ""
        labels = []
        values = []
        colors = []
        if wins > 0:
            labels.append("盈利"); values.append(wins); colors.append("#27ae60")
        if losses > 0:
            labels.append("亏损"); values.append(losses); colors.append("#e74c3c")
        if breakeven > 0:
            labels.append("平持"); values.append(breakeven); colors.append("#95a5a6")
        return """
        <h2>交易盈亏分布</h2>
        <div id="trade-pie" style="max-width:500px;margin:0 auto;"></div>
        <script>
        Plotly.newPlot("trade-pie", [{
            values: """ + json.dumps(values) + """,
            labels: """ + json.dumps(labels) + """,
            type: "pie",
            marker: { colors: """ + json.dumps(colors) + """ },
            textinfo: "label+percent+value",
            hole: 0.3
        }], { height: 350, margin: { t: 20, b: 20 } }, { responsive: true });
        </script>"""

    def _risk_section_html(self, result: dict) -> str:
        equity_data = result.get("equity_curve", [])
        if not equity_data:
            return ""
        try:
            from engine.risk_analysis import generate_risk_report
            ec = pd.Series(
                [d["value"] for d in equity_data],
                index=pd.to_datetime([d["date"] for d in equity_data]),
            )
            risk = generate_risk_report(ec)
            if not risk:
                return ""
        except Exception:
            return ""
        fmt = risk.get("formatted", {})
        cards = ""
        skip_keys = {"总收益率", "年化收益率", "最大回撤"}
        for name, val in fmt.items():
            if name in skip_keys:
                continue
            cards += """
            <div class="risk-card">
                <div class="label">""" + str(name) + """</div>
                <div class="value">""" + str(val) + """</div>
            </div>"""
        return """
        <h2>风险分析指标</h2>
        <div class="risk-grid">""" + cards + """</div>"""

    def generate_html_report(self, result: dict, title: str = "量化回测报告", show_chart: bool = True) -> str:
        metrics = result.get("metrics", {})
        trade_metrics = result.get("trade_metrics", {})
        equity = result.get("equity_curve", [])
        drawdown = result.get("drawdown_curve", [])
        trades = result.get("trades", [])
        final_capital = result.get("final_capital", 0)
        total_return = result.get("total_return", "0%")

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
            metrics_html += """
            <div class="metric-card """ + card_class + """">
                <div class="metric-label">""" + name + """</div>
                <div class="metric-value">""" + str(val) + """</div>
            </div>"""

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
            trade_card_html += """
            <div class="metric-card info">
                <div class="metric-label">""" + name + """</div>
                <div class="metric-value">""" + str(val) + """</div>
            </div>"""

        trades_html = ""
        if trades:
            trades_html = """
            <h2>交易明细</h2>
            <table>
                <thead><tr><th>日期</th><th>操作</th><th>价格</th><th>数量</th><th>收益</th></tr></thead>
                <tbody>"""
            for trade in trades[:50]:
                action_text = "买入" if trade.get("action") == "buy" else "卖出"
                pnl = trade.get("pnl", 0)
                pnl_color = "green" if pnl > 0 else "red"
                trades_html += '<tr><td>' + str(trade.get("date", "")) + '</td><td>' + action_text + '</td><td>' + f"{trade.get('price', 0):.2f}" + '</td><td>' + f"{trade.get('shares', 0):.0f}" + '</td><td style="color:' + pnl_color + '">' + f"{pnl:,.2f}" + '</td></tr>'
            trades_html += "</tbody></table>"

        chart_html = ""
        if show_chart and equity:
            dd_trace = ""
            yaxis_extra = ""
            if drawdown:
                dd_values = json.dumps([d.get("value", 0) for d in drawdown])
                dd_trace = ',\n            {\n                x: dates, y: ' + dd_values + ',\n                type: "scatter", mode: "lines", name: "\u56de\u64a4\u66f2\u7ebf",\n                fill: "tozeroy", line: { color: "#e74c3c", width: 1 },\n                yaxis: "y2"\n            }'
                yaxis_extra = ', yaxis2: { title: "\u56de\u64a4", overlaying: "y", side: "right", rangemode: "tozero" }'
            chart_html = '''
            <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
            <div class="chart-section">
            <h2>资金曲线</h2>
            <div id="chart"></div>
            <script>
            var data = ''' + json.dumps(equity) + ''';
            var dates = data.map(function(d) { return d.date; });
            var values = data.map(function(d) { return d.value; });
            var trace = {
                x: dates, y: values,
                type: "scatter", mode: "lines", name: "资金曲线",
                line: { color: "#1f77b4", width: 2 }
            }''' + dd_trace + ''';
            var layout = {
                title: "回测资金曲线",
                xaxis: { title: "日期" },
                yaxis: { title: "资金", rangemode: "tozero" }''' + yaxis_extra + ''',
                height: 400
            };
            Plotly.newPlot("chart", [trace], layout, { responsive: true });
            </script>
            </div>'''

        heatmap_html = self._monthly_heatmap_html(equity)
        pie_html = self._trade_pie_html(trades)
        risk_html = self._risk_section_html(result)

        html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + title + '''</title>
    <style>''' + self._BASE_CSS + '''</style>
</head>
<body>
    <div class="container">
        <h1>📈 ''' + title + '''</h1>
        <p>报告日期: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''</p>
        <div class="metrics-grid">
            ''' + metrics_html + '''
        </div>
        <div class="metrics-grid">
            ''' + trade_card_html + '''
        </div>
        ''' + risk_html + chart_html + heatmap_html + pie_html + trades_html + '''
        <div class="footer">
            <p>量化选股回测平台 | 自动生成报告</p>
        </div>
    </div>
</body>
</html>'''
        return html

    def generate_csv(self, result: dict, filename: str = "backtest_trades.csv") -> str:
        trades = result.get("trades", [])
        if not trades:
            df = pd.DataFrame(columns=["date", "action", "price", "shares", "pnl"])
        else:
            df = pd.DataFrame(trades)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        return filename

    def generate_json(self, result: dict, filename: str = "backtest_report.json") -> str:
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

    def generate_comparison_html(self, results: list[dict], title: str = "策略对比报告") -> str:
        if not results:
            return "<html><body><h1>无策略数据</h1></body></html>"
        rows = []
        all_equity = []
        risk_rows = []
        for idx, r in enumerate(results):
            name = r.get("strategy_name", f"策略 {idx + 1}")
            m = r.get("metrics", {})
            tm = r.get("trade_metrics", {})
            row = {
                "name": name,
                "total_return": r.get("total_return", "0%"),
                "annual_return": m.get("年化收益率", "N/A"),
                "sharpe": m.get("夏普比率", "N/A"),
                "max_drawdown": m.get("最大回撤", "N/A"),
                "win_rate": tm.get("胜率", m.get("胜率", "N/A")),
                "profit_factor": tm.get("利润因子", "N/A"),
                "trade_count": len(r.get("trades", [])),
                "final_capital": r.get("final_capital", 0),
            }
            rows.append(row)
            equity = r.get("equity_curve", [])
            if equity:
                all_equity.append({"name": name, "data": equity})
            risk_card = {"name": name}
            try:
                from engine.risk_analysis import generate_risk_report
                if equity:
                    ec = pd.Series([d["value"] for d in equity], index=pd.to_datetime([d["date"] for d in equity]))
                    risk = generate_risk_report(ec)
                    if risk:
                        risk_card.update(risk.get("formatted", {}))
            except Exception:
                pass
            risk_rows.append(risk_card)
        def _ps(val):
            try: return float(val)
            except: return -999
        best_idx = max(range(len(rows)), key=lambda i: _ps(rows[i].get("sharpe", -999)))
        hc = "<th>指标</th>"
        for i, r in enumerate(rows):
            cls = ' class="highlight-best"' if i == best_idx else ""
            star = " ⭐" if i == best_idx else ""
            hc += "<th" + cls + ">" + r["name"] + star + "</th>"
        ml = [("总收益率","total_return"),("年化收益率","annual_return"),("夏普比率","sharpe"),("最大回撤","max_drawdown"),("胜率","win_rate"),("利润因子","profit_factor"),("交易次数","trade_count"),("期末资金","final_capital")]
        tr = ""
        for label, key in ml:
            cells = '<td style="font-weight:bold;">' + label + "</td>"
            for i, r in enumerate(rows):
                val = r.get(key, "N/A")
                if key == "final_capital" and isinstance(val, (int, float)): val = f"{val:,.2f}"
                if key == "trade_count": val = str(val)
                cls = ' class="highlight-best"' if i == best_idx else ""
                cells += "<td" + cls + ">" + str(val) + "</td>"
            tr += "<tr>" + cells + "</tr>"
        ct = '<h2>核心指标对比</h2><div style="overflow-x:auto;"><table><thead><tr>' + hc + '</tr></thead><tbody>' + tr + '</tbody></table></div>'
        rt = ""
        if risk_rows and any(len(r) > 1 for r in risk_rows):
            rk = [k for k in risk_rows[0].keys() if k != "name"]
            rh = "<th>风险指标</th>" + "".join("<th>" + r["name"] + "</th>" for r in risk_rows)
            rr = ""
            for key in rk:
                cells = '<td style="font-weight:bold;">' + key + "</td>"
                for r in risk_rows:
                    cells += "<td>" + str(r.get(key, "-")) + "</td>"
                rr += "<tr>" + cells + "</tr>"
            rt = '<h2>风险指标对比</h2><div style="overflow-x:auto;"><table><thead><tr>' + rh + '</tr></thead><tbody>' + rr + '</tbody></table></div>'
        ch = ""
        if all_equity:
            traces = []
            for item in all_equity:
                d = item["data"]
                traces.append({"x": [p["date"] for p in d], "y": [p["value"] for p in d], "type": "scatter", "mode": "lines", "name": item["name"], "line": {"width": 2}})
            ch = '<script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script><h2>权益曲线对比</h2><div id="comparison-chart"></div><script>var traces = ' + json.dumps(traces) + ';Plotly.newPlot("comparison-chart",traces,{title:"策略权益曲线对比",xaxis:{title:"日期"},yaxis:{title:"资金",rangemode:"tozero"},height:450,legend:{orientation:"h",y:-0.15}},{responsive:true});</script>'
        return '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>' + title + '</title><style>' + self._BASE_CSS + '</style></head><body><div class="container"><h1>📊 ' + title + '</h1><p>报告日期: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '</p><p>对比策略数: ' + str(len(results)) + '</p>' + ct + rt + ch + '<div class="footer"><p>量化选股回测平台 | 策略对比报告</p></div></div></body></html>'

    def generate_pdf_report(self, result: dict, title: str = "回测报告", filename: str = "backtest_report.pdf") -> str:
        try:
            return self._generate_pdf_fpdf(result, title, filename)
        except ImportError:
            html_filename = filename.replace(".pdf", "_print.html")
            html = self._generate_print_html(result, title)
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html)
            return html_filename

    def _generate_pdf_fpdf(self, result: dict, title: str, filename: str) -> str:
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        from fpdf import FPDF
        metrics_r = result.get("metrics", {})
        trade_metrics = result.get("trade_metrics", {})
        equity = result.get("equity_curve", [])
        drawdown = result.get("drawdown_curve", [])
        trades = result.get("trades", [])
        cn_font = None
        for fname in ["SimHei", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei", "STHeiti", "Heiti SC"]:
            matches = [f for f in fm.fontManager.ttflist if fname.lower() in f.name.lower()]
            if matches:
                cn_font = matches[0].fname
                break
        if cn_font:
            plt.rcParams["font.sans-serif"] = [fm.FontProperties(fname=cn_font).get_name()]
        plt.rcParams["axes.unicode_minus"] = False
        chart_images = []
        if equity:
            fig, ax = plt.subplots(figsize=(8, 3.5))
            dates = [pd.to_datetime(d["date"]) for d in equity]
            values = [d["value"] for d in equity]
            ax.plot(dates, values, color="#1f77b4", linewidth=1.5)
            ax.set_title("资金曲线", fontsize=14)
            ax.set_ylabel("资金")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150)
            plt.close(fig)
            chart_images.append(("equity", buf))
        if drawdown:
            fig, ax = plt.subplots(figsize=(8, 2.5))
            dd_dates = [pd.to_datetime(d["date"]) for d in drawdown]
            dd_vals = [d.get("value", 0) for d in drawdown]
            ax.fill_between(dd_dates, dd_vals, 0, color="#e74c3c", alpha=0.4)
            ax.plot(dd_dates, dd_vals, color="#e74c3c", linewidth=1)
            ax.set_title("回撤曲线", fontsize=14)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150)
            plt.close(fig)
            chart_images.append(("drawdown", buf))
        if equity:
            try:
                ec = pd.Series([d["value"] for d in equity], index=pd.to_datetime([d["date"] for d in equity]))
                pivot = self.generate_monthly_returns(ec)
                if not pivot.empty:
                    fig, ax = plt.subplots(figsize=(10, max(2, len(pivot) * 0.6 + 1)))
                    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto", vmin=-0.15, vmax=0.15)
                    ax.set_xticks(range(12))
                    ax.set_xticklabels([str(m) for m in range(1, 13)])
                    ax.set_yticks(range(len(pivot)))
                    ax.set_yticklabels(pivot.index)
                    ax.set_title("月度收益率热力图", fontsize=14)
                    fig.colorbar(im, ax=ax, format="%.1%%", shrink=0.8)
                    fig.tight_layout()
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=150)
                    plt.close(fig)
                    chart_images.append(("monthly", buf))
            except: pass
        sell_trades = [t for t in trades if t.get("action") == "sell"]
        if sell_trades:
            wins = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
            losses = sum(1 for t in sell_trades if t.get("pnl", 0) < 0)
            even = len(sell_trades) - wins - losses
            fig, ax = plt.subplots(figsize=(5, 3.5))
            lp, sz, cp = [], [], []
            if wins > 0: lp.append("盈利"); sz.append(wins); cp.append("#27ae60")
            if losses > 0: lp.append("亏损"); sz.append(losses); cp.append("#e74c3c")
            if even > 0: lp.append("平持"); sz.append(even); cp.append("#95a5a6")
            ax.pie(sz, labels=lp, colors=cp, autopct="%1.1f%%", startangle=90, wedgeprops={"width": 0.4})
            ax.set_title("交易盈亏分布", fontsize=14)
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150)
            plt.close(fig)
            chart_images.append(("trades_pie", buf))
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        font_loaded = False
        if cn_font and os.path.exists(cn_font):
            try:
                pdf.add_font("CNFont", "", cn_font, uni=True)
                pdf.add_font("CNFont", "B", cn_font, uni=True)
                pdf.set_font("CNFont", "", 11)
                font_loaded = True
            except: pass
        if not font_loaded:
            pdf.set_font("Helvetica", "", 11)
        pdf.add_page()
        tf = "CNFont" if font_loaded else "Helvetica"
        pdf.set_font(tf, "B", 22)
        pdf.cell(0, 15, title, ln=True, align="C")
        pdf.set_font(tf, "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        pdf.ln(10)
        si = [("初始资金", f"{result.get('initial_capital', 0):,.2f}"), ("期末资金", f"{result.get('final_capital', 0):,.2f}"), ("总收益率", str(result.get("total_return", "0%"))), ("年化收益率", str(metrics_r.get("年化收益率", "N/A"))), ("夏普比率", str(metrics_r.get("夏普比率", "N/A"))), ("最大回撤", str(metrics_r.get("最大回撤", "N/A"))), ("胜率", str(trade_metrics.get("胜率", metrics_r.get("胜率", "N/A")))), ("利润因子", str(trade_metrics.get("利润因子", "N/A")))]
        cw = 90
        for i, (label, value) in enumerate(si):
            x = 10 + (i % 2) * cw
            pdf.set_font(tf, "", 9)
            pdf.set_text_color(120, 120, 120)
            pdf.set_xy(x, pdf.get_y())
            pdf.cell(cw, 5, label, ln=False)
            pdf.set_font(tf, "B", 14)
            pdf.set_text_color(44, 62, 80)
            pdf.set_xy(x, pdf.get_y() + 5)
            pdf.cell(cw, 8, str(value), ln=False)
            if i % 2 == 1: pdf.ln(14)
            elif i == len(si) - 1: pdf.ln(14)
        pdf.set_text_color(0, 0, 0)
        for chart_name, buf in chart_images:
            pdf.add_page()
            buf.seek(0)
            tmp_img = filename.replace(".pdf", "_" + chart_name + ".png")
            with open(tmp_img, "wb") as f:
                f.write(buf.read())
            pdf.image(tmp_img, x=10, w=190)
            try: os.remove(tmp_img)
            except: pass
        pdf.output(filename)
        return filename

    def _generate_print_html(self, result: dict, title: str) -> str:
        base_html = self.generate_html_report(result, title, show_chart=True)
        print_css = """@media print { body { background: white; padding: 0; font-size: 11pt; } .container { max-width: 100%; } .metric-card { box-shadow: none; border: 1px solid #ddd; page-break-inside: avoid; } table { page-break-inside: avoid; } .footer { page-break-before: always; } h1, h2 { page-break-after: avoid; } .chart-section { page-break-inside: avoid; } }"""
        base_html = base_html.replace("</style>", print_css + "\n</style>")
        return base_html

    def export_all(self, result: dict, base_name: str = "report") -> dict:
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
            reports["csv"] = self.generate_csv(result, f"{base_name}_trades.csv")
        except Exception as e:
            reports["csv"] = f"Error: {e}"
        try:
            reports["json"] = self.generate_json(result, f"{base_name}_data.json")
        except Exception as e:
            reports["json"] = f"Error: {e}"
        try:
            reports["pdf"] = self.generate_pdf_report(result, "量化回测报告", f"{base_name}.pdf")
        except Exception as e:
            reports["pdf"] = f"Error: {e}"
        return reports
