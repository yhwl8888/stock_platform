from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import concurrent.futures

from data.fetcher import DataFetcher
from engine.strategy import create_strategy, strategy_registry, get_strategy_label
from engine.backtest import run_backtest
from engine.metrics import format_metrics
from screener.screener import StockScreener, builtin_filters, get_filter_label, get_filter_builder
from trading.paper_trading import PaperTrading
from notification import notifier

app = FastAPI(title="量化选股回测平台", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fetcher = DataFetcher()
paper = PaperTrading()


class BacktestRequest(BaseModel):
    strategy: str
    codes: List[str]
    start: str = "20200101"
    end: str = "20251231"
    initial_capital: float = 1000000.0
    params: dict = {}


class ScreenerRequest(BaseModel):
    conditions: List[dict]
    start: str = "20200101"
    end: str = "20251231"


class OrderRequest(BaseModel):
    code: str
    action: str
    price: float
    shares: int


class BatchQuoteRequest(BaseModel):
    codes: List[str]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stocks")
def list_stocks(keyword: str = ""):
    if keyword:
        df = fetcher.store.search_stocks(keyword)
    else:
        df = fetcher.store.get_basic()
    if df.empty:
        fetcher.fetch_stock_list()
        df = fetcher.store.get_basic()
    return {"data": df.to_dict(orient="records")} if not df.empty else {"data": []}


@app.get("/api/stock/{code}/daily")
def get_stock_daily(code: str, start: str = "20200101", end: str = "20251231"):
    df = fetcher.get_daily_data(code, start, end)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"股票 {code} 数据未找到")
    df = df.reset_index()
    df["date"] = df["date"].astype(str)
    return {"data": df.to_dict(orient="records")}


@app.get("/api/strategies")
def list_strategies():
    strategies = []
    for name, entry in strategy_registry.items():
        cls = entry["cls"]
        import inspect
        params = inspect.signature(cls.__init__).parameters
        param_info = {k: str(v.annotation) for k, v in params.items() if k != "self"}
        strategies.append({"name": name, "label": entry["label"], "params": param_info})
    return {"data": strategies}


@app.post("/api/backtest")
def run_backtest_api(req: BacktestRequest):
    try:
        strategy = create_strategy(req.strategy, **req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data = {}
    for code in req.codes:
        try:
            df = fetcher.ensure_data(code, req.start, req.end)
            if not df.empty:
                data[code] = df
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取{code}数据失败: {str(e)}")
    if not data:
        raise HTTPException(status_code=404, detail="没有获取到有效数据")
    try:
        result = run_backtest(strategy, data, req.initial_capital)
    except Exception as e:
        import traceback
        detail = f"回测执行失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=detail)

    equity = []
    for dt, val in result.equity_curve.items():
        equity.append({"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 2)})
    drawdown = []
    for dt, val in result.drawdown_curve.items():
        drawdown.append({"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 4)})

    return {
        "metrics": format_metrics(result.metrics),
        "trade_metrics": result.trade_metrics,
        "equity_curve": equity,
        "drawdown_curve": drawdown,
        "trades": result.trades,
        "signals": [{"code": s.code, "date": s.date, "action": s.action, "price": s.price, "reason": s.reason} for s in result.signals],
        "final_capital": round(result.final_capital, 2),
        "total_return": f"{result.total_return * 100:.2f}%",
    }


@app.get("/api/screener/filters")
def list_filters():
    filters = [{"name": k, "label": v["label"], "description": v["builder"]().desc} for k, v in builtin_filters.items()]
    return {"data": filters}


@app.post("/api/screener/run")
def run_screener(req: ScreenerRequest):
    fetcher.fetch_stock_list()
    stocks_df = fetcher.store.get_basic()
    if stocks_df.empty:
        raise HTTPException(status_code=500, detail="股票列表为空")

    codes = stocks_df["code"].tolist()[:100]
    data = {}
    for code in codes:
        try:
            df = fetcher.ensure_data(code, req.start, req.end)
            if not df.empty and len(df) > 20:
                data[code] = df
        except Exception:
            continue

    stock_list = fetcher.store.get_basic()
    name_map = dict(zip(stock_list["code"], stock_list["name"])) if not stock_list.empty else {}
    screener = StockScreener(name_map=name_map)
    for cond in req.conditions:
        name = cond.get("name")
        params = cond.get("params", {})
        builder = get_filter_builder(name)
        if builder:
            screener.add_condition(builder(**params))

    result_df = screener.run(data)
    if result_df.empty:
        return {"data": []}
    return {"data": result_df.to_dict(orient="records")}


@app.get("/api/paper/account")
def get_account():
    position_codes = list(paper.positions.keys())
    
    if position_codes:
        try:
            from data.tencent_source import fetch_realtime_quotes
            quotes = fetch_realtime_quotes(position_codes, timeout=5.0)
            for code, quote in quotes.items():
                price = quote.get("price", 0)
                if price > 0 and code in paper.positions:
                    paper.positions[code].current_price = price
        except Exception:
            pass
    
    positions_raw = paper.get_positions_df()
    return {
        "initial_capital": paper.initial_capital,
        "cash": round(paper.cash, 2),
        "total_assets": round(paper.total_assets, 2),
        "total_pnl": round(paper.total_pnl, 2),
        "total_pnl_pct": f"{paper.total_pnl_pct:.2f}%",
        "positions": positions_raw.to_dict(orient="records") if not positions_raw.empty else [],
    }


@app.post("/api/paper/order")
def place_order(req: OrderRequest):
    order = paper.place_order(req.code, req.action, req.price, req.shares)
    
    if order.status == "filled" and notifier.is_enabled():
        stock_list = fetcher.store.get_basic()
        name_map = dict(zip(stock_list["code"], stock_list["name"])) if not stock_list.empty else {}
        stock_name = name_map.get(req.code, req.code)
        
        notifier.send_trade_notification(
            code=req.code,
            name=stock_name,
            action=req.action,
            price=req.price,
            shares=req.shares,
            amount=req.price * req.shares
        )
    
    return {
        "order_id": order.order_id,
        "status": "filled" if order.status == "filled" else "cancelled",
    }


@app.get("/api/paper/history")
def get_history():
    df = paper.get_history_df()
    return {"data": df.to_dict(orient="records") if not df.empty else []}


@app.post("/api/paper/reset")
def reset_account():
    paper.reset()
    return {"status": "ok"}


@app.get("/api/index/{code}")
def get_index(code: str = "000001", start: str = "20200101", end: str = "20251231"):
    df = fetcher.fetch_index_daily(code, start, end)
    return {"data": df.to_dict(orient="records")} if not df.empty else {"data": []}


@app.get("/api/quote/{code}")
def get_real_time_quote(code: str):
    """获取实时行情（尝试网络，失败返回最近收盘价）"""
    return get_quote_internal(code)


def get_quote_internal(code: str):
    """获取单只股票行情的内部实现"""
    import threading
    from data.tencent_source import fetch_single_quote, check_tencent_network
    
    result = {"data": None, "error": None}
    code = code.strip().zfill(6)
    
    # Step 1: Try Tencent API (faster, more reliable in China)
    def fetch_tencent():
        try:
            data = fetch_single_quote(code, timeout=3.0)
            if data and data.get("price", 0) > 0:
                result["data"] = data
                return
        except Exception:
            pass
        
        # Step 2: Fallback to AKShare
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            if not df.empty and "代码" in df.columns:
                df["代码"] = df["代码"].astype(str).str.zfill(6)
                row = df[df["代码"] == code]
                if not row.empty:
                    r = row.iloc[0]
                    result["data"] = {
                        "code": code,
                        "name": r.get("名称", ""),
                        "price": float(r.get("最新价", 0)),
                        "open": float(r.get("开盘价", 0)),
                        "high": float(r.get("最高价", 0)),
                        "low": float(r.get("最低价", 0)),
                        "volume": float(r.get("成交量", 0)),
                        "change_pct": float(r.get("涨跌幅", 0)),
                        "source": "akshare",
                    }
                    return
        except Exception:
            pass
    
    t = threading.Thread(target=fetch_tencent)
    t.daemon = True
    t.start()
    t.join(timeout=8)
    
    if result["data"]:
        return result["data"]
    
    # Step 3: Fallback to local cached data (last close price)
    df = fetcher.ensure_data(code)
    if not df.empty:
        last = df.iloc[-1]
        stock_list = fetcher.store.get_basic()
        name_map = dict(zip(stock_list["code"], stock_list["name"])) if not stock_list.empty else {}
        return {
            "code": code,
            "name": name_map.get(code, ""),
            "price": float(last["close"]),
            "open": float(last["open"]),
            "high": float(last["high"]),
            "low": float(last["low"]),
            "volume": int(last["volume"]),
            "source": "local",
        }
    return {"code": code, "name": "", "price": 0, "source": "none"}


@app.post("/api/quote/batch")
def get_batch_quotes(req: BatchQuoteRequest):
    """批量获取实时行情（同时查询多只股票）"""
    import threading
    from data.tencent_source import fetch_realtime_quotes
    
    results = []
    realtime_data = {}
    
    def fetch_batch():
        try:
            # Try Tencent API first
            data = fetch_realtime_quotes(req.codes, timeout=8.0)
            if data:
                for code, quote in data.items():
                    if quote.get("price", 0) > 0:
                        realtime_data[code] = quote
                if realtime_data:
                    return
        except Exception:
            pass
        
        # Fallback to AKShare
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            if not df.empty and "代码" in df.columns:
                df["代码"] = df["代码"].astype(str).str.zfill(6)
                for code in req.codes:
                    row = df[df["代码"] == code]
                    if not row.empty:
                        r = row.iloc[0]
                        realtime_data[code] = {
                            "code": code,
                            "name": r.get("名称", ""),
                            "price": float(r.get("最新价", 0)),
                            "open": float(r.get("开盘价", 0)),
                            "high": float(r.get("最高价", 0)),
                            "low": float(r.get("最低价", 0)),
                            "volume": float(r.get("成交量", 0)),
                            "change_pct": float(r.get("涨跌幅", 0)),
                            "source": "akshare",
                        }
        except Exception:
            pass
    
    t = threading.Thread(target=fetch_batch)
    t.daemon = True
    t.start()
    t.join(timeout=12)
    
    for code in req.codes:
        code = code.strip().zfill(6)
        if code in realtime_data:
            results.append(realtime_data[code])
        else:
            result = get_quote_internal(code)
            results.append(result)
    
    return {"data": results}


@app.get("/api/watchlist")
def get_watchlist():
    df = fetcher.store.get_watchlist()
    if df.empty:
        return {"data": []}
    codes = df["code"].tolist()
    quotes = {}
    try:
        from data.tencent_source import fetch_realtime_quotes
        data = fetch_realtime_quotes(codes, timeout=8.0)
        for code, quote in data.items():
            if quote.get("price", 0) > 0:
                quotes[code] = {
                    "price": quote.get("price", 0),
                    "change_pct": quote.get("change_pct", 0),
                    "volume": quote.get("volume", 0),
                    "source": quote.get("source", "tencent")
                }
    except Exception:
        pass
    
    rows = []
    for _, row in df.iterrows():
        code = row["code"]
        q = quotes.get(code, {})
        rows.append({
            "code": code,
            "name": row.get("name", ""),
            "added_at": row.get("added_at", ""),
            "price": q.get("price", 0),
            "change_pct": q.get("change_pct", 0),
            "source": q.get("source", "local")
        })
    return {"data": rows}


class WatchlistRequest(BaseModel):
    code: str
    name: str = ""


@app.post("/api/watchlist/add")
def add_to_watchlist(req: WatchlistRequest):
    success = fetcher.store.add_watchlist(req.code, req.name)
    return {"success": success, "code": req.code}


@app.post("/api/watchlist/remove")
def remove_from_watchlist(req: WatchlistRequest):
    success = fetcher.store.remove_watchlist(req.code)
    return {"success": success, "code": req.code}


@app.get("/api/watchlist/check/{code}")
def check_watchlist(code: str):
    is_in = fetcher.store.is_in_watchlist(code)
    return {"code": code, "is_in_watchlist": is_in}


@app.get("/api/quote/intraday/{code}")
def get_intraday_quote(code: str):
    """获取分时实时行情数据"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_minute(symbol=code, period="1", adjust="qfq")
        if df is not None and not df.empty:
            df = df.tail(300)
            return {
                "code": code,
                "data": df.to_dict(orient="records"),
                "source": "realtime"
            }
    except Exception as e:
        pass
    return {"code": code, "data": [], "source": "none"}


@app.get("/api/news/{code}")
def get_stock_news(code: str):
    """获取股票新闻公告"""
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=code)
        if df is not None and not df.empty:
            news_list = []
            for _, row in df.head(10).iterrows():
                news_list.append({
                    "title": str(row.get("新闻标题", "")),
                    "url": str(row.get("新闻链接", "")),
                    "datetime": str(row.get("发布时间", ""))
                })
            return {"code": code, "data": news_list}
    except Exception:
        pass
    return {"code": code, "data": []}


@app.get("/api/news/market")
def get_market_news():
    """获取市场新闻快讯"""
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol="全球重要指数")
        if df is not None and not df.empty:
            news_list = []
            for _, row in df.head(20).iterrows():
                news_list.append({
                    "title": str(row.get("新闻标题", "")),
                    "url": str(row.get("新闻链接", "")),
                    "datetime": str(row.get("发布时间", ""))
                })
            return {"data": news_list}
    except Exception:
        pass
    return {"data": []}


class PriceAlertRequest(BaseModel):
    code: str
    condition: str
    threshold: float
    enabled: bool = True


@app.get("/api/alerts")
def get_price_alerts():
    df = fetcher.store.get_price_alerts()
    if df.empty:
        return {"data": []}
    return {"data": df.to_dict(orient="records")}


@app.post("/api/alerts/add")
def add_price_alert(req: PriceAlertRequest):
    success = fetcher.store.add_price_alert(req.code, req.condition, req.threshold, req.enabled)
    return {"success": success, "code": req.code, "condition": req.condition}


@app.post("/api/alerts/remove")
def remove_price_alert(req: PriceAlertRequest):
    success = fetcher.store.remove_price_alert(req.code, req.condition)
    return {"success": success, "code": req.code}


@app.get("/api/alerts/check")
def check_price_alerts():
    alerts = fetcher.store.get_price_alerts()
    if alerts.empty:
        return {"alerts": [], "triggered": []}
    
    triggered = []
    codes = [a["code"] for _, a in alerts.iterrows() if a.get("enabled", True)]
    
    try:
        from data.tencent_source import fetch_realtime_quotes
        quotes = fetch_realtime_quotes(codes, timeout=8.0)
        
        stock_list = fetcher.store.get_basic()
        name_map = dict(zip(stock_list["code"], stock_list["name"])) if not stock_list.empty else {}
        
        for _, alert in alerts.iterrows():
            if not alert.get("enabled", True):
                continue
            code = alert["code"]
            condition = alert["condition"]
            threshold = alert["threshold"]
            
            quote = quotes.get(code, {})
            price = quote.get("price", 0)
            
            if price > 0:
                change_pct = quote.get("change_pct", 0)
                name = quote.get("name", name_map.get(code, code))
                
                is_triggered = False
                if condition == "above" and price > threshold:
                    is_triggered = True
                elif condition == "below" and price < threshold:
                    is_triggered = True
                elif condition == "rise_pct" and change_pct > threshold:
                    is_triggered = True
                elif condition == "fall_pct" and change_pct < -threshold:
                    is_triggered = True
                
                if is_triggered:
                    triggered.append({
                        "code": code,
                        "condition": condition,
                        "threshold": threshold,
                        "current_price": price,
                        "current_change_pct": change_pct
                    })
                    
                    stock_name = name_map.get(code, name)
                    
                    if notifier.is_enabled():
                        notifier.send_price_alert(
                            code=code,
                            name=stock_name,
                            price=price,
                            change_pct=change_pct,
                            condition=condition,
                            threshold=threshold
                        )
    except Exception:
        pass
    
    return {"alerts": alerts.to_dict(orient="records"), "triggered": triggered}




# --- Strategy Comparison & Report Generation ---

class CompareRequest(BaseModel):
    strategies: List[dict]
    codes: List[str]
    start: str = "20200101"
    end: str = "20251231"
    initial_capital: float = 1000000.0


class ReportRequest(BaseModel):
    strategy: str
    codes: List[str]
    start: str = "20200101"
    end: str = "20251231"
    initial_capital: float = 1000000.0
    params: dict = {}
    format: str = "html"


@app.post("/api/backtest/compare")
def compare_strategies(req: CompareRequest):
    """Multi-strategy backtest comparison"""
    data = {}
    for code in req.codes:
        try:
            df = fetcher.ensure_data(code, req.start, req.end)
            if not df.empty:
                data[code] = df
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Data fetch failed for {code}: {e}")
    if not data:
        raise HTTPException(status_code=404, detail="No valid data")

    results = []
    for s in req.strategies:
        name = s.get("name", "")
        params = s.get("params", {})
        label = s.get("label", get_strategy_label(name))
        try:
            strategy = create_strategy(name, **params)
            result = run_backtest(strategy, data, req.initial_capital)
            equity = [{"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 2)}
                      for dt, val in result.equity_curve.items()]
            drawdown = [{"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 4)}
                        for dt, val in result.drawdown_curve.items()]
            results.append({
                "strategy_name": label, "strategy_key": name,
                "metrics": format_metrics(result.metrics), "raw_metrics": result.metrics,
                "trade_metrics": result.trade_metrics,
                "equity_curve": equity, "drawdown_curve": drawdown,
                "trades": result.trades,
                "signals": [{"code": sig.code, "date": sig.date, "action": sig.action, "price": sig.price, "reason": sig.reason}
                            for sig in result.signals],
                "final_capital": round(result.final_capital, 2),
                "total_return": f"{result.total_return * 100:.2f}%",
            })
        except Exception as e:
            results.append({"strategy_name": label, "strategy_key": name, "error": str(e)})

    risk_comparison = []
    for r in results:
        if "error" in r:
            continue
        equity = r.get("equity_curve", [])
        if equity:
            try:
                from engine.risk_analysis import generate_risk_report
                ec = pd.Series([d["value"] for d in equity], index=pd.to_datetime([d["date"] for d in equity]))
                risk = generate_risk_report(ec)
                risk_comparison.append({"strategy": r["strategy_name"], "risk": risk.get("formatted", {}), "raw_risk": risk.get("raw", {})})
            except Exception:
                pass

    return {"results": results, "risk_comparison": risk_comparison}


@app.post("/api/report/generate")
def generate_report(req: ReportRequest):
    """Generate backtest report"""
    try:
        strategy = create_strategy(req.strategy, **req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = {}
    for code in req.codes:
        try:
            df = fetcher.ensure_data(code, req.start, req.end)
            if not df.empty:
                data[code] = df
        except Exception:
            pass
    if not data:
        raise HTTPException(status_code=404, detail="No valid data")

    result = run_backtest(strategy, data, req.initial_capital)
    equity = [{"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 2)}
              for dt, val in result.equity_curve.items()]
    drawdown = [{"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 4)}
                for dt, val in result.drawdown_curve.items()]

    result_dict = {
        "strategy_name": strategy.name, "metrics": format_metrics(result.metrics),
        "trade_metrics": result.trade_metrics,
        "equity_curve": equity, "drawdown_curve": drawdown,
        "trades": result.trades,
        "final_capital": round(result.final_capital, 2),
        "total_return": f"{result.total_return * 100:.2f}%",
        "initial_capital": req.initial_capital,
    }

    from engine.report_generator import ReportGenerator
    gen = ReportGenerator()

    if req.format == "html":
        html = gen.generate_html_report(result_dict, f"Backtest Report - {strategy.name}")
        return {"format": "html", "content": html}
    elif req.format == "csv":
        csv_path = gen.generate_csv(result_dict)
        return {"format": "csv", "path": csv_path}
    elif req.format == "json":
        json_path = gen.generate_json(result_dict)
        return {"format": "json", "path": json_path}
    else:
        reports = gen.export_all(result_dict)
        return {"format": "all", "reports": reports}


@app.get("/api/risk/{code}")
def get_risk_analysis(code: str, start: str = "20200101", end: str = "20251231"):
    """Risk analysis for a single stock"""
    df = fetcher.get_daily_data(code, start, end)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Stock {code} data not found")

    equity = df["close"]
    from engine.risk_analysis import calculate_risk_metrics, generate_risk_report, rolling_sharpe, rolling_volatility, drawdown_analysis
    risk = calculate_risk_metrics(equity)
    report = generate_risk_report(equity)
    dd = drawdown_analysis(equity)

    return {"code": code, "risk_metrics": risk, "risk_report": report, "drawdown_analysis": dd}


@app.get("/api/data/sources")
def list_data_sources():
    """List available data sources and their status"""
    from data.tencent_source import check_tencent_network
    from data.fetcher import _check_network, _check_hist_network
    sources = []
    ak_ok = _check_network() and _check_hist_network()
    sources.append({"name": "AKShare", "type": "historical", "available": ak_ok})
    try:
        tc_ok = check_tencent_network(timeout=3)
    except Exception:
        tc_ok = False
    sources.append({"name": "Tencent Finance", "type": "realtime", "available": tc_ok})
    try:
        from data.sina_source import check_sina_network
        sina_ok = check_sina_network(timeout=3)
    except Exception:
        sina_ok = False
    sources.append({"name": "Sina Finance", "type": "historical+realtime", "available": sina_ok})
    try:
        from data.eastmoney_source import check_eastmoney_network
        em_ok = check_eastmoney_network(timeout=3)
    except Exception:
        em_ok = False
    sources.append({"name": "Eastmoney", "type": "historical+realtime", "available": em_ok})
    sources.append({"name": "Local Generated", "type": "offline", "available": True})
    return {"sources": sources}


@app.post("/api/backtest/batch")
def batch_backtest(req: CompareRequest):
    """Run backtest for multiple strategies in batch and return comparison with reports"""
    data = {}
    for code in req.codes:
        try:
            df = fetcher.ensure_data(code, req.start, req.end)
            if not df.empty:
                data[code] = df
        except Exception:
            pass
    if not data:
        raise HTTPException(status_code=404, detail="No valid data")

    results = []
    for s in req.strategies:
        name = s.get("name", "")
        params = s.get("params", {})
        label = s.get("label", get_strategy_label(name))
        try:
            strategy = create_strategy(name, **params)
            result = run_backtest(strategy, data, req.initial_capital)
            equity = [{"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": round(float(val), 2)}
                      for dt, val in result.equity_curve.items()]
            results.append({
                "strategy_name": label, "strategy_key": name,
                "metrics": format_metrics(result.metrics),
                "trade_metrics": result.trade_metrics,
                "equity_curve": equity,
                "final_capital": round(result.final_capital, 2),
                "total_return": f"{result.total_return * 100:.2f}%",
            })
        except Exception as e:
            results.append({"strategy_name": label, "strategy_key": name, "error": str(e)})

    # Generate comparison report
    from engine.report_generator import ReportGenerator
    gen = ReportGenerator()
    valid_results = [r for r in results if "error" not in r]
    comparison_html = gen.generate_comparison_html(valid_results, "Strategy Comparison") if valid_results else ""

    return {"results": results, "comparison_html": comparison_html}


@app.on_event("shutdown")
def shutdown():
    fetcher.close()


class NotificationSettings(BaseModel):
    chat_id: str = ""
    user_id: str = ""
    enabled: bool = True


@app.get("/api/notification/status")
def get_notification_status():
    return {
        "enabled": notifier.is_enabled(),
    }


@app.post("/api/notification/test")
def test_notification():
    if notifier.is_enabled():
        success = notifier.send_message(content="🧪 测试消息：量化平台通知功能正常！")
        return {"success": success, "message": "测试消息已发送" if success else "发送失败"}
    return {"success": False, "message": "飞书未登录，请在终端运行 lark-cli auth login"}


@app.post("/api/data/regenerate")
def regenerate_sample_data():
    """重新生成样本数据"""
    try:
        from data.generator import generate_sample_data
        generate_sample_data()
        fetcher = DataFetcher()
        count = len(fetcher.store.get_basic())
        return {"success": True, "message": f"已重新生成数据，当前 {count} 只股票"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/stats")
def get_stats():
    """获取系统统计信息"""
    try:
        stocks = fetcher.store.get_basic()
        alerts = fetcher.store.get_price_alerts()
        watchlist = fetcher.store.get_watchlist()
        return {
            "stocks_count": len(stocks),
            "alerts_count": len(alerts),
            "watchlist_count": len(watchlist),
            "notifier_enabled": notifier.is_enabled(),
        }
    except Exception as e:
        return {"error": str(e)}
