import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import httpx
import json
import time
from datetime import datetime
import streamlit.components.v1 as components

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="量化选股回测平台", layout="wide", page_icon="📈")

st.markdown("""
<style>
    /* 全局样式 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #2d5a87 100%);
    }
    [data-testid="stSidebar"] .stRadio > div {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        color: white !important;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 8px;
        transition: all 0.3s;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.2);
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
        background: rgba(46, 204, 113, 0.8) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* 标题样式 */
    h1 {
        color: #1e3a5f;
        font-weight: 700;
        border-bottom: 3px solid #2ecc71;
        padding-bottom: 10px;
    }
    h2, h3 {
        color: #2c5aa0;
    }
    
    /* 卡片样式 */
    .stCard {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(52, 152, 219, 0.4);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 5px 20px rgba(46, 204, 113, 0.4);
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3498db;
    }
    
    /* 指标卡片 */
    [data-testid="stMetricValue"] {
        color: #2c5aa0;
        font-weight: 600;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #f0f2f6;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        color: white;
    }
    
    /* 成功/警告/错误消息 */
    .stSuccess {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-radius: 10px;
    }
    .stWarning {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
        border-radius: 10px;
    }
    .stError {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-radius: 10px;
    }
    
    /* 数据表格样式 */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* 分隔线 */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, #3498db, #2ecc71);
        margin: 20px 0;
    }
    
    /* 自定义卡片容器 */
    .custom-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #3498db;
    }
    .custom-card-success {
        border-left-color: #2ecc71;
    }
    .custom-card-warning {
        border-left-color: #f39c12;
    }
    .custom-card-danger {
        border-left-color: #e74c3c;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
    <h1 style="font-size: 2.5em; margin-bottom: 10px; border: none;">📈 量化选股回测平台</h1>
    <p style="color: #666; font-size: 1.1em;">A股数据 | 策略回测 | 智能选股 | 模拟交易</p>
</div>
""", unsafe_allow_html=True)

nav_items = [
    ("股票数据", "📊"),
    ("策略回测", "🧪"),
    ("策略对比", "📉"),
    ("策略对比增强", "🔀"),
    ("报告生成", "📄"),
    ("选股筛选", "🔍"),
    ("模拟交易", "💰"),
    ("自选股", "⭐"),
    ("实时行情", "📈"),
    ("价格预警", "🔔"),
    ("通知设置", "🔗"),
    ("关于", "ℹ️"),
    ("数据源管理", "🗄️"),
    ("资金流向", "💰"),
    ("北向资金", "🧭"),
    ("龙虎榜", "🐉"),
    ("行业排名", "🏭")
]

st.sidebar.markdown("""
<div style="text-align: center; padding: 15px 0; margin-bottom: 20px; border-bottom: 2px solid rgba(255,255,255,0.3);">
    <h2 style="color: white !important; font-size: 1.5em; margin: 0;">🧭 导航菜单</h2>
</div>
""", unsafe_allow_html=True)

nav_labels = [f"{icon} {name}" for name, icon in nav_items]
nav_dict = {f"{icon} {name}": name for name, icon in nav_items}
selected_nav = st.sidebar.radio("nav", nav_labels)
page = nav_dict[selected_nav]

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; padding: 15px; color: rgba(255,255,255,0.7); font-size: 0.9em;">
    <p>版本: v1.0.0</p>
    <p>Powered by Streamlit</p>
</div>
""", unsafe_allow_html=True)


def safe_api(url: str, method: str = "GET", data: dict = None, timeout: int = 60) -> dict:
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            if method == "GET":
                resp = client.get(f"{API_BASE}{url}")
            else:
                resp = client.post(f"{API_BASE}{url}", json=data)
            resp.raise_for_status()
            return resp.json()
        return {}
    except httpx.ConnectError:
        st.error(f"无法连接后端，请确保已启动: uvicorn api.main:app --reload")
        return {}
    except Exception as e:
        st.error(f"请求失败: {e}")
        return {}


def resolve_code_input(code_text):
    """Parse user input codes, handling disambiguation for ambiguous codes like 000001"""
    import re
    codes = [c.strip().lower() for c in re.split(r'[,;\s]+', code_text) if c.strip()]
    resolved = []
    for c in codes:
        if c.startswith(('sh', 'sz', 'bj')) and len(c) == 8:
            resolved.append(c)
            continue
        info = safe_api(f'/api/code/{c}', timeout=5)
        if info and info.get('ambiguous'):
            for opt in info.get('options', []):
                if opt['type'] == 'stock':
                    resolved.append(opt['full_code'])
                    break
        elif info and info.get('info'):
            resolved.append(info['info'].get('full_code', c))
        else:
            resolved.append(c)
    return resolved


if page == "股票数据":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">📊 A股数据浏览</h3>
        <p style="color: #666; margin-top: 5px;">浏览股票日线数据，查看K线图表</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("##### 🔍 搜索股票")
        keyword = st.text_input("搜索", placeholder="输入代码或名称...")
        search_btn = st.button("🔍 搜索", use_container_width=True)
    with col2:
        st.markdown("##### 📋 股票列表")

    if search_btn or keyword:
        resp = safe_api(f"/api/stocks?keyword={keyword}")
    else:
        resp = safe_api("/api/stocks")

    stocks = resp.get("data", [])
    if stocks:
        df = pd.DataFrame(stocks)
        cols = st.columns([3, 1])
        with cols[0]:
            st.dataframe(df, use_container_width=True, hide_index=True)
        with cols[1]:
            st.markdown("""
            <div class="custom-card custom-card-success">
                <p style="margin: 0; font-size: 0.9em;">💡 数据为前复权价格</p>
            </div>
            """, unsafe_allow_html=True)
            if len(df) <= 60:
                st.markdown("""
                <div class="custom-card custom-card-warning">
                    <p style="margin: 0; font-size: 0.9em;">📁 本地样本数据（非实时）</p>
                </div>
                """, unsafe_allow_html=True)

        code_name_map = dict(zip(df["code"], df["name"]))
        sel_code = st.selectbox("选择股票查看日线",
                                df["code"].tolist(),
                                format_func=lambda c: f"{c} - {code_name_map.get(c, '')}")
        if sel_code:
            quote = safe_api(f"/api/quote/{sel_code}", timeout=10)
            if quote and quote.get("price", 0) > 0:
                src = "📡 实时" if quote.get("source") == "realtime" else "📁 本地"
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("最新价", f"{quote['price']:.2f}", 
                           delta=f"{quote.get('change_pct', 0):.2f}%" if quote.get("change_pct") else None)
                col2.metric("开盘", f"{quote.get('open', 0):.2f}")
                col3.metric("最高", f"{quote.get('high', 0):.2f}")
                col4.metric("最低", f"{quote.get('low', 0):.2f}")
                col5.caption(f"{src} | 成交量: {quote.get('volume', 0):,.0f}")
            
            with st.spinner("加载日线数据..."):
                resp2 = safe_api(f"/api/stock/{sel_code}/daily")
            data = resp2.get("data", [])
            if data:
                df2 = pd.DataFrame(data)
                df2["date"] = pd.to_datetime(df2["date"])
                df2 = df2.sort_values("date")

                fig = make_subplots(
                    rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.7, 0.3]
                )
                fig.add_trace(go.Candlestick(
                    x=df2["date"], open=df2["open"], high=df2["high"],
                    low=df2["low"], close=df2["close"], name="K线"
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=df2["date"], y=df2["volume"], name="成交量",
                    marker_color="rgba(0,150,255,0.5)"
                ), row=2, col=1)
                fig.update_layout(height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                tab1, tab2, tab3, tab4, tab5 = st.tabs(["数据表", "基本信息", "资金流向", "概念板块", "研报"])
                with tab1:
                    st.dataframe(df2, use_container_width=True, hide_index=True)
                with tab2:
                    latest = df2.iloc[-1]
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("最新收益", f"{latest['close']:.2f}")
                    col2.metric("最高", f"{latest['high']:.2f}")
                    col3.metric("最低", f"{latest['low']:.2f}")
                    col4.metric("成交量", f"{latest['volume']:.0f}")
                with tab3:
                    ff_resp = safe_api(f"/api/fund-flow/{sel_code}?mode=daily")
                    if ff_resp and ff_resp.get("data"):
                        ff_df = pd.DataFrame(ff_resp["data"])
                        st.dataframe(ff_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("暂无资金流向数据 available")
                with tab4:
                    concept_resp = safe_api(f"/api/concept/{sel_code}")
                    if concept_resp and concept_resp.get("data"):
                        concept_df = pd.DataFrame(concept_resp["data"])
                        st.dataframe(concept_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("暂无概念板块数据")
                with tab5:
                    reports_resp = safe_api(f"/api/reports/{sel_code}")
                    if reports_resp and reports_resp.get("data"):
                        reports_df = pd.DataFrame(reports_resp["data"])
                        st.dataframe(reports_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("暂无研报数据")
    else:
        st.info("搜索或加载股票数据")

elif page == "策略回测":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🧪 策略回测</h3>
        <p style="color: #666; margin-top: 5px;">选择策略和股票，运行回测分析</p>
    </div>
    """, unsafe_allow_html=True)

    resp = safe_api("/api/strategies")
    strategies = resp.get("data", [])

    col1, col2 = st.columns([1, 2])
    with col1:
        strategy_options = {s["label"]: s["name"] for s in strategies}
        sel_label = st.selectbox("选择策略", list(strategy_options.keys())) if strategy_options else "均线金叉死叉"
        sel_strategy = strategy_options.get(sel_label, "ma_cross")
        strategy_info = next((s for s in strategies if s["name"] == sel_strategy), None)

        col_a, col_b = st.columns([3, 1])
        with col_a:
            codes_input = st.text_input("股票代码（逗号或空格分隔）", "000001,600519")
        with col_b:
            stock_resp = safe_api("/api/stocks")
            stock_map = {s["code"]: s["name"] for s in stock_resp.get("data", [])}
            import re
            codes = [c.strip() for c in re.split(r'[,，\s]+', codes_input) if c.strip()]
            code_labels = [f"{c} - {stock_map.get(c, '?')}" for c in codes]
            if code_labels:
                st.caption(" | ".join(code_labels))

        start = st.text_input("开始日期", "20230101")
        end = st.text_input("结束日期", "20251231")
        capital = st.number_input("初始资金", value=1000000.0, step=100000.0)

        param_labels = {
            "fast_period": "快线周期", "slow_period": "慢线周期",
            "period": "计算周期", "oversold": "超卖阈值", "overbought": "超买阈值",
            "std_dev": "标准差倍数",
        }
        params = {}
        if strategy_info:
            st.markdown("##### 策略参数")
            for pname in strategy_info.get("params", {}):
                label = param_labels.get(pname, pname)
                default = 20 if "period" in pname.lower() or "slow" in pname.lower() else (
                    5 if "fast" in pname.lower() else 30 if "oversold" in pname.lower() else 70 if "overbought" in pname.lower() else 2.0 if "std" in pname.lower() else 10)
                params[pname] = st.number_input(label, value=float(default) if isinstance(default, float) else default)

        run_btn = st.button("运行回测", type="primary", use_container_width=True)

    with col2:
        if run_btn and codes:
            with st.spinner("回测进行中..."):
                req = {
                    "strategy": sel_strategy,
                    "codes": codes,
                    "start": start.replace("-", ""),
                    "end": end.replace("-", ""),
                    "initial_capital": float(capital),
                    "params": params,
                }
                result = safe_api("/api/backtest", method="POST", data=req, timeout=60)

            if result and "equity_curve" in result:
                st.subheader("回测结果")
                m = result.get("metrics", {})

                cols = st.columns(4)
                cols[0].metric("最终资产", f"{result.get('final_capital', 0):,.2f}")
                cols[1].metric("总收益率", result.get("total_return", "0%"))
                cols[2].metric("夏普比率", m.get("夏普比率", "0"))
                cols[3].metric("最大回撤", m.get("最大回撤", "0%"))

                mcols = st.columns(4)
                mcols[0].metric("年化收益率", m.get("年化收益率", "0%"))
                mcols[1].metric("年化波动率", m.get("年化波动率", "0%"))
                mcols[2].metric("胜率", m.get("胜率", "0%"))
                mcols[3].metric("交易天数", m.get("交易天数", "0"))

                equity = result.get("equity_curve", [])
                if equity:
                    edf = pd.DataFrame(equity)
                    edf["date"] = pd.to_datetime(edf["date"])
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                    fig.add_trace(go.Scatter(x=edf["date"], y=edf["value"],
                                             mode="lines", name="资金曲线",
                                             line=dict(color="green", width=2)), row=1, col=1)
                    dd = result.get("drawdown_curve", [])
                    if dd:
                        ddf = pd.DataFrame(dd)
                        ddf["date"] = pd.to_datetime(ddf["date"])
                        fig.add_trace(go.Scatter(x=ddf["date"], y=ddf["value"] * 100,
                                                 mode="lines", name="回撤",
                                                 fill="tozeroy",
                                                 line=dict(color="red", width=1)), row=2, col=1)
                    fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)

                trades = result.get("trades", [])
                if trades:
                    with st.expander(f"交易明细 ({len(trades)} 笔)", expanded=False):
                        st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)

                signals = result.get("signals", [])
                if signals:
                    with st.expander(f"信号明细 ({len(signals)} 条)", expanded=False):
                        st.dataframe(pd.DataFrame(signals), use_container_width=True, hide_index=True)
                
                # Save to comparison
                col1, col2 = st.columns([3, 1])
                with col2:
                    st.markdown("##### 操作")
                    save_btn = st.button("💾 保存到对比", type="secondary", use_container_width=True)
                    if save_btn:
                        if "backtest_results" not in st.session_state:
                            st.session_state.backtest_results = []
                        
                        m = result.get("metrics", {})
                        comparison_data = {
                            "label": sel_label or strategy_info.get("label", ""),
                            "final_capital": result.get("final_capital", 0),
                            "total_return": result.get("total_return", "0%"),
                            "metrics": {
                                "最终资产": m.get("最终资产", ""),
                                "总收益率": m.get("总收益率", ""),
                                "夏普比率": m.get("夏普比率", ""),
                                "最大回撤": m.get("最大回撤", ""),
                                "年化收益率": m.get("年化收益率", ""),
                                "年化波动率": m.get("年化波动率", ""),
                                "胜率": m.get("胜率", ""),
                                "交易天数": m.get("交易天数", ""),
                            },
                            "equity_curve": result.get("equity_curve", []),
                            "drawdown_curve": result.get("drawdown_curve", []),
                            "trades": result.get("trades", []),
                            "signals": signals,
                        }
                        st.session_state.backtest_results.append(comparison_data)
                        st.success("已保存到对比列表")
                        st.rerun()
            else:
                st.warning("回测未产生结果，请检查参数")

elif page == "选股筛选":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🔍 选股筛选器</h3>
        <p style="color: #666; margin-top: 5px;">按技术指标多条件筛选股票</p>
    </div>
    """, unsafe_allow_html=True)

    resp = safe_api("/api/screener/filters")
    available_filters = resp.get("data", [])
    filter_map = {f["label"]: f for f in available_filters}

    st.markdown("### ➕ 添加筛选条件")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sel_label = st.selectbox("条件类型", list(filter_map.keys()))
    with col2:
        st.markdown("##### &nbsp;")
        add_btn = st.button("添加条件", use_container_width=True)

    if "screen_conditions" not in st.session_state:
        st.session_state.screen_conditions = []

    if add_btn and sel_label:
        sel_filter = filter_map[sel_label]
        st.session_state.screen_conditions.append({
            "name": sel_filter["name"],
            "params": {},
            "desc": sel_filter["description"]
        })

    if st.session_state.screen_conditions:
        st.markdown("##### 已选条件")
        cols = st.columns([3, 1, 1])
        for i, cond in enumerate(st.session_state.screen_conditions):
            with st.container():
                c1, c2 = st.columns([4, 1])
                c1.info(f"{i+1}. {cond['desc']}")
                if c2.button("删除", key=f"del_{i}", use_container_width=True):
                    st.session_state.screen_conditions.pop(i)
                    st.rerun()

    col1, col2 = st.columns([1, 1])
    with col1:
        screen_start = st.text_input("数据起始日期", "20240101")
    with col2:
        screen_btn = st.button("开始筛选", type="primary", use_container_width=True)

    if screen_btn:
        if not st.session_state.screen_conditions:
            st.warning("请至少添加一个筛选条件")
        else:
            with st.spinner("筛选进行中（约需30秒）..."):
                req = {
                    "conditions": st.session_state.screen_conditions,
                    "start": screen_start,
                    "end": datetime.now().strftime("%Y%m%d"),
                }
                result = safe_api("/api/screener/run", method="POST", data=req, timeout=120)

            data = result.get("data", [])
            if data:
                df = pd.DataFrame(data)
                st.success(f"筛选出 {len(df)} 只股票")
                st.dataframe(df, use_container_width=True, hide_index=True)

                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 导出CSV", csv, "screener_result.csv", "text/csv")
            else:
                st.warning("没有符合条件的股票")

elif page == "模拟交易":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">💰 模拟交易</h3>
        <p style="color: #666; margin-top: 5px;">虚拟盘交易练习，跟踪持仓和收益</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 账户概览", "📝 下单交易", "📜 历史记录"])

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("""
            <div class="custom-card custom-card-success">
                <h4 style="margin: 0 0 15px 0;">💳 账户信息</h4>
            </div>
            """, unsafe_allow_html=True)
            resp = safe_api("/api/paper/account")
            if resp:
                cols = st.columns(2)
                cols[0].metric("总资产", f"{resp.get('total_assets', 0):,.2f}")
                cols[1].metric("可用资金", f"{resp.get('cash', 0):,.2f}")
                cols2 = st.columns(2)
                cols2[0].metric("总收益", f"{resp.get('total_pnl', 0):,.2f}", 
                               delta=f"{resp.get('total_pnl_pct', '0%')}")
                cols2[1].metric("收益率", resp.get('total_pnl_pct', '0%'))

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 重置账户", use_container_width=True):
                    safe_api("/api/paper/reset", method="POST")
                    st.success("账户已重置")
                    st.rerun()

        with col2:
            positions = resp.get("positions", []) if resp else []
            if positions:
                st.markdown("""
                <div class="custom-card">
                    <h4 style="margin: 0 0 15px 0;">📈 当前持仓</h4>
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True)
            else:
                st.markdown("""
                <div class="custom-card custom-card-warning">
                    <p style="margin: 0;">📭 当前无持仓</p>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("""
            <div class="custom-card">
                <h4 style="margin: 0 0 15px 0;">📝 委托下单</h4>
            </div>
            """, unsafe_allow_html=True)
            code = st.text_input("股票代码", "600519").strip()
            action = st.radio("交易方向", ["买入", "卖出"])
            price = st.number_input("价格", value=200.0, step=0.01, format="%.2f")
            shares = st.number_input("数量（股）", value=100, step=100, min_value=100)
            if st.button("📤 提交委托", type="primary", use_container_width=True):
                api_action = "buy" if action == "买入" else "sell"
                resp = safe_api("/api/paper/order", method="POST", data={
                    "code": code, "action": api_action,
                    "price": float(price), "shares": int(shares)
                })
                if resp:
                    status = resp.get("status", "")
                    if status == "filled":
                        st.success(f"✅ 订单已成交: {code} {api_action} {shares}股 @ {price}")
                    else:
                        st.error("❌ 订单未成交（资金不足或持仓不足）")
                    st.rerun()
        with col2:
            st.markdown("""
            <div class="custom-card">
                <h4 style="margin: 0 0 15px 0;">📊 快速数据</h4>
            </div>
            """, unsafe_allow_html=True)
            sel_code = st.text_input("查看行情", "600519")
            if sel_code:
                quote = safe_api(f"/api/quote/{sel_code}", timeout=15)
                if quote and quote.get("price", 0) > 0:
                    src = "实时" if quote.get("source") == "realtime" else "本地"
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"现价", f"{quote['price']:.2f}", 
                             delta=f"{quote.get('change_pct', 0):.2f}%" if quote.get('change_pct') else None)
                    c2.metric("开盘", f"{quote['open']:.2f}")
                    c3.metric("最高", f"{quote['high']:.2f}")
                    c4.metric("最低", f"{quote['low']:.2f}")
                    st.caption(f"数据来源: {src}")
                resp = safe_api(f"/api/stock/{sel_code}/daily", timeout=15)
                data = resp.get("data", [])
                if data:
                    df = pd.DataFrame(data)
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").tail(60)
                    fig = go.Figure(data=[go.Candlestick(
                        x=df["date"], open=df["open"], high=df["high"],
                        low=df["low"], close=df["close"],
                        increasing_line_color='#2ecc71',
                        decreasing_line_color='#e74c3c'
                    )])
                    fig.update_layout(height=350, xaxis_rangeslider_visible=False,
                                     paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        resp = safe_api("/api/paper/history")
        data = resp.get("data", [])
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info("暂无交易记录")

elif page == "策略对比":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">📉 策略对比</h3>
        <p style="color: #666; margin-top: 5px;">使用多选策略直接调用对比接口，一键对比回测结果</p>
    </div>
    """, unsafe_allow_html=True)

    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = []

    resp = safe_api("/api/strategies")
    strategies = resp.get("data", [])
    strategy_options = {s["label"]: s["name"] for s in strategies}

    col1, col2 = st.columns([1, 3])
    with col1:
        sel_labels = st.multiselect(
            "选择策略（多选）",
            list(strategy_options.keys()),
            default=list(strategy_options.keys())[:2] if len(strategy_options) >= 2 else list(strategy_options.keys())
        )
        sel_strategies = [strategy_options[lbl] for lbl in sel_labels]

        codes_input = st.text_input("股票代码", "000001,600519", key="duibi_codes")
        import re
        codes = [c.strip() for c in re.split(r'[,,\s]+', codes_input) if c.strip()]

        start_date = st.text_input("开始日期", "20230101", key="duibi_start")
        end_date = st.text_input("结束日期", "20251231", key="duibi_end")
        capital = st.number_input("初始资金", value=1000000.0, step=100000.0, key="duibi_capital")

        run_compare_btn = st.button("🚀 运行对比", type="primary", use_container_width=True)

        st.markdown("---")
        if st.button("🗑️ 清空对比", use_container_width=True):
            st.session_state.backtest_results.clear()
            st.rerun()

    with col2:
        if run_compare_btn and sel_strategies and codes:
            with st.spinner("对比回测进行中..."):
                strategy_dicts = [{"name": s, "params": {}, "label": lbl} for lbl, s in strategy_options.items() if s in sel_strategies]
                req = {
                    "strategies": strategy_dicts,
                    "codes": codes,
                    "start": start_date.replace("-", ""),
                    "end": end_date.replace("-", ""),
                    "initial_capital": float(capital),
                }
                result = safe_api("/api/backtest/compare", method="POST", data=req, timeout=120)

            if result and result.get("results"):
                st.session_state.backtest_results = []
                for r in result["results"]:
                    m = r.get("metrics", {})
                    st.session_state.backtest_results.append({
                        "label": r.get("strategy_name", r.get("label", r.get("strategy", ""))),
                        "final_capital": r.get("final_capital", 0),
                        "total_return": r.get("total_return", "0%"),
                        "metrics": m,
                        "equity_curve": r.get("equity_curve", []),
                        "drawdown_curve": r.get("drawdown_curve", []),
                        "trades": r.get("trades", []),
                    })
                st.success(f"✅ 对比完成，共 {len(st.session_state.backtest_results)} 个策略")
                st.rerun()
            elif result:
                st.warning(result.get("message", "对比未产生结果"))

        if st.session_state.backtest_results:
            st.markdown("### 📊 指标对比表")
            comp_data = []
            for i, r in enumerate(st.session_state.backtest_results):
                m = r.get("metrics", {})
                comp_data.append({
                    "序号": i + 1,
                    "策略名称": r.get("label", ""),
                    "最终资产": f"{r.get('final_capital', 0):,.2f}",
                    "总收益率": r.get("total_return", ""),
                    "夏普比率": m.get("夏普比率", ""),
                    "最大回撒": m.get("最大回撒", ""),
                    "年化收益率": m.get("年化收益率", ""),
                    "胜率": m.get("胜率", ""),
                    "交易天数": m.get("交易天数", ""),
                })
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

            st.markdown("### 📈 资金曲线对比")
            fig = go.Figure()
            colors = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6", "#1abc9c", "#e91e63", "#00bcd4"]
            for i, r in enumerate(st.session_state.backtest_results):
                equity = r.get("equity_curve", [])
                if equity:
                    edf = pd.DataFrame(equity)
                    edf["date"] = pd.to_datetime(edf["date"])
                    fig.add_trace(go.Scatter(
                        x=edf["date"], y=edf["value"],
                        mode="lines", name=r.get("label", ""),
                        line=dict(color=colors[i % len(colors)], width=3)
                    ))
            fig.update_layout(height=500, xaxis_rangeslider_visible=False,
                             legend=dict(orientation="h", y=1.08, x=0),
                             paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📉 回撒对比")
            fig2 = go.Figure()
            for i, r in enumerate(st.session_state.backtest_results):
                drawdown = r.get("drawdown_curve", [])
                if drawdown:
                    ddf = pd.DataFrame(drawdown)
                    ddf["date"] = pd.to_datetime(ddf["date"])
                    fig2.add_trace(go.Scatter(
                        x=ddf["date"], y=ddf["value"] * 100,
                        mode="lines", name=r.get("label", ""),
                        line=dict(color=colors[i % len(colors)], width=2),
                        fill="tozeroy"
                    ))
            fig2.update_layout(height=400, xaxis_rangeslider_visible=False,
                              legend=dict(orientation="h", y=1.08, x=0),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("### 📊 风险指标对比")
            risk_data = []
            for r in st.session_state.backtest_results:
                m = r.get("metrics", {})
                risk_data.append({
                    "策略": r.get("label", ""),
                    "夏普比率": m.get("夏普比率", "N/A"),
                    "最大回撒": m.get("最大回撒", "N/A"),
                    "年化波动率": m.get("年化波动率", "N/A"),
                    "年化收益率": m.get("年化收益率", "N/A"),
                    "胜率": m.get("胜率", "N/A"),
                })
            st.dataframe(pd.DataFrame(risk_data), use_container_width=True, hide_index=True)
        else:
            st.markdown("""
            <div class="custom-card custom-card-warning">
                <p style="margin: 0;">📭 暂无对比结果，请在左侧选择策略并点击「运行对比」</p>
            </div>
            """, unsafe_allow_html=True)
elif page == "策略对比增强":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🔀 策略对比增强</h3>
        <p style="color: #666; margin-top: 5px;">多策略参数化对比，支持自定义参数配置</p>
    </div>
    """, unsafe_allow_html=True)

    resp = safe_api("/api/strategies")
    all_strategies = resp.get("data", [])
    strategy_map = {s["label"]: s for s in all_strategies}

    st.markdown("### ➕ 选择对比策略")
    selected_labels = st.multiselect(
        "选择要对比的策略（可多选）",
        list(strategy_map.keys()),
        default=list(strategy_map.keys())[:2] if len(strategy_map) >= 2 else list(strategy_map.keys()),
        key="enh_compare_strategies"
    )

    if "enh_compare_configs" not in st.session_state:
        st.session_state.enh_compare_configs = {}

    if selected_labels:
        st.markdown("### ⚙️ 策略参数配置")
        param_labels = {
            "fast_period": "快线周期", "slow_period": "慢线周期",
            "period": "计算周期", "oversold": "超卖阈值", "overbought": "超买阈值",
            "std_dev": "标准差倍数",
        }

        configs = []
        for label in selected_labels:
            sinfo = strategy_map[label]
            with st.expander(f"🔧 {label} 参数", expanded=False):
                params = {}
                for pname in sinfo.get("params", {}):
                    plabel = param_labels.get(pname, pname)
                    default = 20 if "period" in pname.lower() or "slow" in pname.lower() else (
                        5 if "fast" in pname.lower() else 30 if "oversold" in pname.lower() else 70 if "overbought" in pname.lower() else 2.0 if "std" in pname.lower() else 10)
                    val = st.number_input(plabel, value=float(default) if isinstance(default, float) else int(default), key=f"enh_{sinfo['name']}_{pname}")
                    params[pname] = val
            configs.append({"strategy": sinfo["name"], "label": label, "params": params})

        st.markdown("### 📅 回测设置")
        col1, col2, col3 = st.columns(3)
        with col1:
            enh_codes = st.text_input("股票代码", "000001,600519", key="enh_codes")
        with col2:
            enh_start = st.text_input("开始日期", "20230101", key="enh_start")
        with col3:
            enh_end = st.text_input("结束日期", "20251231", key="enh_end")

        enh_capital = st.number_input("初始资金", value=1000000.0, step=100000.0, key="enh_capital")

        if st.button("🚀 运行增强对比", type="primary", use_container_width=True):
            import re as _re
            codes_list = [c.strip() for c in _re.split(r'[,,\s]+', enh_codes) if c.strip()]
            if not codes_list:
                st.warning("请输入股票代码")
            else:
                with st.spinner("增强对比回测进行中..."):
                    strategy_dicts = [{"name": c["strategy"], "params": c["params"], "label": c.get("label", c["strategy"])} for c in configs]
                    req = {
                        "strategies": strategy_dicts,
                        "codes": codes_list,
                        "start": enh_start.replace("-", ""),
                        "end": enh_end.replace("-", ""),
                        "initial_capital": float(enh_capital),
                    }
                    result = safe_api("/api/backtest/compare", method="POST", data=req, timeout=120)

                if result and result.get("results"):
                    st.success(f"✅ 增强对比完成，共 {len(result['results'])} 个策略")

                    st.markdown("### 📊 综合对比表")
                    rows = []
                    for r in result["results"]:
                        m = r.get("metrics", {})
                        rows.append({
                            "策略": r.get("label", r.get("strategy", "")),
                            "最终资产": f"{r.get('final_capital', 0):,.2f}",
                            "总收益率": r.get("total_return", ""),
                            "夏普比率": m.get("夏普比率", ""),
                            "最大回撒": m.get("最大回撒", ""),
                            "年化收益率": m.get("年化收益率", ""),
                            "年化波动率": m.get("年化波动率", ""),
                            "胜率": m.get("胜率", ""),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    st.markdown("### 📈 叠加资金曲线")
                    colors = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6", "#1abc9c", "#e91e63", "#00bcd4"]
                    fig = go.Figure()
                    for i, r in enumerate(result["results"]):
                        eq = r.get("equity_curve", [])
                        if eq:
                            edf = pd.DataFrame(eq)
                            edf["date"] = pd.to_datetime(edf["date"])
                            fig.add_trace(go.Scatter(
                                x=edf["date"], y=edf["value"],
                                mode="lines", name=r.get("label", ""),
                                line=dict(color=colors[i % len(colors)], width=3)
                            ))
                    fig.update_layout(height=500, xaxis_rangeslider_visible=False,
                                     legend=dict(orientation="h", y=1.08, x=0),
                                     paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### 📊 风险指标对比")
                    risk_rows = []
                    for r in result["results"]:
                        m = r.get("metrics", {})
                        risk_rows.append({
                            "策略": r.get("label", r.get("strategy", "")),
                            "夏普比率": m.get("夏普比率", "N/A"),
                            "最大回撒": m.get("最大回撒", "N/A"),
                            "年化波动率": m.get("年化波动率", "N/A"),
                            "年化收益率": m.get("年化收益率", "N/A"),
                            "胜率": m.get("胜率", "N/A"),
                            "交易天数": m.get("交易天数", "N/A"),
                        })
                    st.dataframe(pd.DataFrame(risk_rows), use_container_width=True, hide_index=True)
                elif result:
                    st.warning(result.get("message", "对比未产生结果"))
    else:
        st.info("请在上方选择要对比的策略")
elif page == "报告生成":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">📄 报告生成</h3>
        <p style="color: #666; margin-top: 5px;">生成策略回测报告，支持多种格式导出</p>
    </div>
    """, unsafe_allow_html=True)

    resp = safe_api("/api/strategies")
    report_strategies = resp.get("data", [])
    strategy_options = {s["label"]: s["name"] for s in report_strategies}

    with st.form("report_form"):
        st.markdown("### 📋 报告参数")
        col1, col2 = st.columns(2)
        with col1:
            rep_sel_label = st.selectbox("选择策略", list(strategy_options.keys())) if strategy_options else ""
            rep_strategy = strategy_options.get(rep_sel_label, "ma_cross")
            rep_codes = st.text_input("股票代码（逗号分隔）", "000001,600519")
        with col2:
            rep_start = st.text_input("开始日期", "20230101", key="rep_start")
            rep_end = st.text_input("结束日期", "20251231", key="rep_end")
            rep_capital = st.number_input("初始资金", value=1000000.0, step=100000.0, key="rep_capital")

        rep_format = st.selectbox("导出格式", ["HTML", "CSV", "JSON", "All"], index=0)

        submitted = st.form_submit_button("📥 生成报告", type="primary", use_container_width=True)

    if submitted:
        import re as _re
        codes_list = [c.strip() for c in _re.split(r'[,,\s]+', rep_codes) if c.strip()]
        if not codes_list:
            st.warning("请输入股票代码")
        else:
            with st.spinner("正在生成报告..."):
                req = {
                    "strategy": rep_strategy,
                    "codes": codes_list,
                    "start": rep_start.replace("-", ""),
                    "end": rep_end.replace("-", ""),
                    "initial_capital": float(rep_capital),
                    "format": rep_format.lower(),
                }
                result = safe_api("/api/report/generate", method="POST", data=req, timeout=120)

            if result:
                if rep_format == "HTML" or rep_format == "All":
                    html_content = result.get("html", result.get("report", ""))
                    if html_content:
                        st.markdown("### 📄 HTML 报告")
                        components.html(html_content, height=800, scrolling=True)
                    else:
                        st.info("未获取到 HTML 报告内容")

                if rep_format == "CSV" or rep_format == "All":
                    csv_data = result.get("csv", "")
                    if csv_data:
                        st.markdown("### 📊 CSV 数据")
                        if isinstance(csv_data, str):
                            csv_bytes = csv_data.encode("utf-8-sig")
                        else:
                            csv_bytes = str(csv_data).encode("utf-8-sig")
                        st.download_button("📥 下载 CSV", csv_bytes, "report.csv", "text/csv")

                if rep_format == "JSON" or rep_format == "All":
                    json_data = result.get("json", result.get("data", ""))
                    if json_data:
                        st.markdown("### 📋 JSON 数据")
                        json_str = json.dumps(json_data, ensure_ascii=False, indent=2) if isinstance(json_data, (dict, list)) else str(json_data)
                        st.download_button("📥 下载 JSON", json_str.encode("utf-8"), "report.json", "application/json")
                        with st.expander("预览 JSON", expanded=False):
                            st.code(json_str, language="json")

                if rep_format not in ("HTML", "CSV", "JSON", "All"):
                    st.success("报告已生成")
                    st.json(result)
            else:
                st.error("报告生成失败，请检查参数或后端服务")
elif page == "自选股":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">⭐ 自选股管理</h3>
        <p style="color: #666; margin-top: 5px;">添加关注的股票，实时查看行情</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### ➕ 添加自选")
        new_code = st.text_input("add_code", placeholder="输入股票代码...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        add_btn = st.button("➕ 添加到自选", use_container_width=True)
    
    if add_btn and new_code:
        code = new_code.strip().zfill(6)
        resp = safe_api(f"/api/stocks?keyword={code}")
        stocks = resp.get("data", [])
        name = ""
        if stocks:
            for s in stocks:
                if s.get("code") == code:
                    name = s.get("name", "")
                    break
        safe_api("/api/watchlist/add", method="POST", data={"code": code, "name": name})
        st.success(f"✅ 已添加 {code} 到自选")
        st.rerun()
    
    st.markdown("### 📊 我的自选股")
    resp = safe_api("/api/watchlist", timeout=30)
    watchlist = resp.get("data", [])
    
    if watchlist:
        df = pd.DataFrame(watchlist)
        
        cols = st.columns([1, 2, 1, 1, 1, 1])
        cols[0].caption("代码")
        cols[1].caption("名称")
        cols[2].caption("最新价")
        cols[3].caption("涨跌幅")
        cols[4].caption("来源")
        cols[5].caption("操作")
        
        for i, row in df.iterrows():
            cols = st.columns([1, 2, 1, 1, 1, 1])
            cols[0].write(row.get("code", ""))
            cols[1].write(row.get("name", ""))
            price = row.get("price", 0)
            change = row.get("change_pct", 0)
            if price > 0:
                cols[2].metric("价", f"{price:.2f}", delta=f"{change:.2f}%" if change else None)
            else:
                cols[2].write("-")
            cols[3].write(f"{change:.2f}%" if change else "-")
            cols[4].write("实时" if row.get("source") == "realtime" else "本地")
            if cols[5].button("🗑️", key=f"del_{row.get('code')}"):
                safe_api("/api/watchlist/remove", method="POST", data={"code": row.get("code")})
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 📈 自选股实时行情")
        codes = [w.get("code") for w in watchlist]
        if codes:
            resp2 = safe_api("/api/quote/batch", method="POST", data={"codes": codes}, timeout=60)
            quotes = resp2.get("data", [])
            if quotes:
                rows = []
                for q in quotes:
                    rows.append({
                        "代码": q.get("code", ""),
                        "名称": q.get("name", ""),
                        "最新价": q.get("price", 0),
                        "涨跌幅": f"{q.get('change_pct', 0):.2f}%",
                        "开盘": q.get("open", 0),
                        "最高": q.get("high", 0),
                        "最低": q.get("low", 0),
                        "成交量": q.get("volume", 0)
                    })
                df_quotes = pd.DataFrame(rows)
                st.dataframe(df_quotes, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div class="custom-card custom-card-warning">
            <p style="margin: 0;">📭 暂无自选股，请添加股票到自选</p>
        </div>
        """, unsafe_allow_html=True)

elif page == "实时行情":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">📈 实时行情监控</h3>
        <p style="color: #666; margin-top: 5px;">实时显示多只股票的最新行情</p>
    </div>
    """, unsafe_allow_html=True)
    
    default_codes = "000001,600519,600036,000858,601318"
    codes_input = st.text_input("股票代码（逗号分隔）", default_codes)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        refresh_btn = st.button("🔄 刷新行情", type="primary", use_container_width=True)
    
    if refresh_btn or codes_input:
        codes = [c.strip() for c in codes_input.replace("，", ",").split(",") if c.strip()]
        if codes:
            with st.spinner("正在获取实时行情..."):
                resp = safe_api("/api/quote/batch", method="POST", 
                               data={"codes": codes}, timeout=60)
            
            quotes = resp.get("data", [])
            if quotes:
                rows = []
                for q in quotes:
                    rows.append({
                        "代码": q.get("code", ""),
                        "名称": q.get("name", ""),
                        "最新价": q.get("price", 0),
                        "涨跌幅": f"{q.get('change_pct', 0):.2f}%",
                        "开盘": q.get("open", 0),
                        "最高": q.get("high", 0),
                        "最低": q.get("low", 0),
                        "成交量": q.get("volume", 0),
                        "来源": "实时" if q.get("source") == "realtime" else "本地"
                    })
                
                df = pd.DataFrame(rows)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 📊 行情列表")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                with col2:
                    st.markdown("### 📈 涨跌幅 Top 5")
                    try:
                        df["涨跌幅数值"] = df["涨跌幅"].str.replace("%", "").astype(float)
                        df_sorted = df.sort_values("涨跌幅数值", ascending=False).head(5)
                    except:
                        df_sorted = df.head(5)
                    st.dataframe(df_sorted[["代码", "名称", "最新价", "涨跌幅"]], 
                                use_container_width=True, hide_index=True)
                
                st.markdown("### 📉 跌幅 Top 5")
                try:
                    df_bottom = df.sort_values("涨跌幅数值", ascending=True).head(5)
                except:
                    df_bottom = df.tail(5)
                st.dataframe(df_bottom[["代码", "名称", "最新价", "涨跌幅"]], 
                            use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("### 💾 导出数据")
                csv = df.drop(columns=["涨跌幅数值"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 下载CSV", csv, "realtime_quotes.csv", "text/csv")
            else:
                st.markdown("""
                <div class="custom-card custom-card-warning">
                    <p style="margin: 0;">⚠️ 未获取到任何行情数据</p>
                </div>
                """, unsafe_allow_html=True)

elif page == "价格预警":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🔔 价格预警</h3>
        <p style="color: #666; margin-top: 5px;">设置股票价格/涨跌幅预警条件，实时监控触发</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        st.markdown("##### ➕ 添加预警")
        alert_code = st.text_input("alert_code", placeholder="股票代码...")
    with col2:
        st.markdown("##### 📋 预警条件")
        condition = st.selectbox("condition", 
            ["above", "below", "rise_pct", "fall_pct"],
            index=0,
            format_func=lambda x: {
                "above": "💹 价格高于",
                "below": "📉 价格低于",
                "rise_pct": "🚀 涨幅大于",
                "fall_pct": "⚡ 跌幅大于"
            }.get(x, x))
    with col3:
        st.markdown("##### 📊 阈值")
        threshold = st.number_input("threshold", value=10.0, step=0.5)
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        add_alert_btn = st.button("➕ 添加预警", use_container_width=True)
    
    if add_alert_btn and alert_code:
        code = alert_code.strip().zfill(6)
        safe_api("/api/alerts/add", method="POST", 
                data={"code": code, "condition": condition, "threshold": threshold})
        st.success(f"✅ 已添加预警: {code} {condition} {threshold}")
        st.rerun()
    
    st.markdown("### 📋 当前预警")
    col1, col2 = st.columns([1, 4])
    with col1:
        check_btn = st.button("🔄 检查预警", use_container_width=True)
    if check_btn:
        with st.spinner("正在检查..."):
            resp = safe_api("/api/alerts/check", timeout=30)
            triggered = resp.get("triggered", [])
            if triggered:
                st.markdown("""
                <div class="custom-card custom-card-danger">
                    <h4 style="margin: 0 0 10px 0;">⚠️ 以下预警已触发:</h4>
                </div>
                """, unsafe_allow_html=True)
                for t in triggered:
                    st.warning(f"🚨 **{t['code']}**: 当前价 ¥{t['current_price']:.2f}, 涨跌幅 {t['current_change_pct']:.2f}%")
            else:
                st.success("✅ 暂无预警触发")
    
    resp = safe_api("/api/alerts", timeout=15)
    alerts = resp.get("data", [])
    if alerts:
        df = pd.DataFrame(alerts)
        df["条件"] = df["condition"].map({
            "above": "价格高于",
            "below": "价格低于",
            "rise_pct": "涨幅大于",
            "fall_pct": "跌幅大于"
        })
        df["状态"] = df["enabled"].apply(lambda x: "✅ 启用" if x else "❌ 禁用")
        st.dataframe(df[["code", "条件", "threshold", "状态"]], use_container_width=True, hide_index=True)
        
        st.markdown("### 🗑️ 删除预警")
        cols = st.columns([1, 3, 1])
        for i, alert in enumerate(alerts):
            if cols[2].button(f"🗑️ 删除 {alert['code']}", key=f"del_alert_{i}"):
                safe_api("/api/alerts/remove", method="POST", 
                        data={"code": alert["code"], "condition": alert["condition"]})
                st.rerun()
    else:
        st.markdown("""
        <div class="custom-card custom-card-warning">
            <p style="margin: 0;">📭 暂无预警设置</p>
        </div>
        """, unsafe_allow_html=True)

elif page == "通知设置":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🔗 通知设置</h3>
        <p style="color: #666; margin-top: 5px;">配置飞书机器人自动发送通知</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        <div class="custom-card">
            <h4 style="margin: 0 0 15px 0;">🔔 飞书通知状态</h4>
        </div>
        """, unsafe_allow_html=True)
        
        resp = safe_api("/api/notification/status", timeout=10)
        is_enabled = resp.get("enabled", False)
        
        if is_enabled:
            st.success("✅ 飞书已连接，通知功能��启")
        else:
            st.warning("❌ 飞书未连接，通知功能关闭")
        
        st.markdown("""
        <div class="custom-card custom-card-success">
            <h4 style="margin: 0 0 15px 0;">💡 如何启用通知</h4>
            <ol style="padding-left: 20px; line-height: 1.8;">
                <li>在终端运行 <code>lark-cli auth login</code> 完成飞书登录</li>
                <li>确保已在飞书开放平台创建机器人并获取 App ID 和 Secret</li>
                <li>点击下方「发送测试消息」按钮验证连接</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="custom-card">
            <h4 style="margin: 0 0 15px 0;">📤 发送测试消息</h4>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📤 发送测试消息", use_container_width=True):
            with st.spinner("正在发送..."):
                resp = safe_api("/api/notification/test", method="POST", timeout=30)
                if resp.get("success"):
                    st.success("✅ " + resp.get("message", ""))
                else:
                    st.error("❌ " + resp.get("message", ""))
        
        st.markdown("---")
        st.markdown("""
        <div class="custom-card">
            <h4 style="margin: 0 0 15px 0;">📋 通知类型</h4>
            <ul style="padding-left: 20px; line-height: 1.8;">
                <li>🔔 <b>价格预警</b>: 触发预警时自动发送通知</li>
                <li>💰 <b>交易通知</b>: 模拟交易成交时发送通知</li>
                <li>🧪 <b>回测完成</b>: 回测完成后发送结果通知</li>
                <li>⭐ <b>自选股动态</b>: 自选股价格变动时通知</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

elif page == "关于":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">ℹ️ 关于平台</h3>
        <p style="color: #666; margin-top: 5px;">了解量化选股回测平台</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        <div class="custom-card">
            <h4 style="margin: 0 0 15px 0;">🔧 技术栈</h4>
            <ul style="list-style: none; padding: 0;">
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">🚀 <b>后端</b>: FastAPI + SQLite</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">🎨 <b>前端</b>: Streamlit + Plotly</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">⚡ <b>回测引擎</b>: 自研事件驱动引擎</li>
                <li style="padding: 8px 0;">📊 <b>数据源</b>: AKShare (在线) / 本地生成 (离线)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="custom-card custom-card-success">
            <h4 style="margin: 0 0 15px 0;">💡 数据说明</h4>
            <ul style="list-style: none; padding: 0; font-size: 0.9em;">
                <li style="padding: 5px 0;">✅ <b>网络可用时</b>: 自动从 AKShare 获取全市场 5000+ 只股票的真实前复权数据</li>
                <li style="padding: 5px 0;">✅ <b>网络不可用时</b>: 使用本地生成的 50+ 只样本股模拟数据</li>
                <li style="padding: 5px 0;">✅ <b>价格类型</b>: 前复权价格（已处理分红送股除权）</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="custom-card">
            <h4 style="margin: 0 0 15px 0;">✨ 功能特性</h4>
            <ul style="list-style: none; padding: 0;">
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">📈 <b>K线数据浏览</b>: 查看任意 A 股的日线行情</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">🧪 <b>策略回测</b>: 支持 MA、RSI、布林带、MACD 等多种策略</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">🔍 <b>选股筛选</b>: 按技术指标多条件筛选股票</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">💰 <b>模拟交易</b>: 模拟买卖，跟踪持仓和收益</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">⭐ <b>自选股</b>: 添加关注股票，实时查看行情</li>
                <li style="padding: 8px 0; border-bottom: 1px solid #eee;">🔔 <b>价格预警</b>: 设置价格/涨跌幅预警</li>
                <li style="padding: 8px 0;">📊 <b>策略对比</b>: 对比不同策略的回测表现</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="custom-card custom-card-warning">
            <h4 style="margin: 0 0 15px 0;">🚀 启动方式</h4>
            <pre style="background: #f5f5f5; padding: 10px; border-radius: 8px; font-size: 0.85em; overflow-x: auto;">
# 方式1: 单命令启动
cd stock_platform
python run.py

# 方式2: 分别启动
python -m uvicorn api.main:app --reload --port 8000
python -m streamlit run web/app.py
            </pre>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # System Stats
    st.markdown("### 📊 系统统计")
    resp = safe_api("/api/stats", timeout=10)
    if resp and "stocks_count" in resp:
        cols = st.columns(4)
        cols[0].metric("股票数量", resp.get("stocks_count", 0))
        cols[1].metric("预警数量", resp.get("alerts_count", 0))
        cols[2].metric("自选数量", resp.get("watchlist_count", 0))
        cols[3].metric("飞书通知", "✅ 已开启" if resp.get("notifier_enabled") else "❌ 未开启")
    
    # Regenerate data button
    st.markdown("### 🔄 数据管理")
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 重新生成样本数据", use_container_width=True):
            with st.spinner("正在重新生成数据..."):
                resp = safe_api("/api/data/regenerate", method="POST", timeout=120)
                if resp.get("success"):
                    st.success(resp.get("message", ""))
                    st.rerun()
                else:
                    st.error(resp.get("message", ""))
    with col2:
        st.caption("重新生成所有样本股票的历史数据")
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 20px; color: #999; font-size: 0.9em;">
        <p>📊 量化选股回测平台 v1.0.0 | Powered by Streamlit + FastAPI</p>
        <p>© 2024 All Rights Reserved</p>
    </div>
    """, unsafe_allow_html=True)

elif page == "数据源管理":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🗄️ 数据源管理</h3>
        <p style="color: #666; margin-top: 5px;">查看和管理系统数据源的可用性</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 4])
    with col1:
        refresh_sources = st.button("🔄 刷新数据源", type="primary", use_container_width=True)

    if refresh_sources or True:
        with st.spinner("正在获取数据源信息..."):
            resp = safe_api("/api/data/sources", timeout=15)

        sources = resp.get("data", resp.get("sources", []))
        if sources:
            st.markdown("### 📦 数据源列表")
            for src in sources:
                name = src.get("name", "Unknown")
                src_type = src.get("type", src.get("source_type", "N/A"))
                available = src.get("available", src.get("enabled", False))
                status_icon = "✅" if available else "❌"
                status_text = "可用" if available else "不可用"
                border_color = "#2ecc71" if available else "#e74c3c"

                st.markdown(f"""
                <div class="custom-card" style="border-left-color: {border_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0;">{status_icon} {name}</h4>
                            <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">类型: {src_type}</p>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: {'#2ecc71' if available else '#e74c3c'}; font-weight: bold;">{status_text}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            cols = st.columns(4)
            available_count = sum(1 for s in sources if s.get("available", s.get("enabled", False)))
            cols[0].metric("数据源总数", len(sources))
            cols[1].metric("可用", available_count)
            cols[2].metric("不可用", len(sources) - available_count)
            cols[3].metric("可用率", f"{available_count/len(sources)*100:.0f}%" if sources else "N/A")
        else:
            st.markdown("""
            <div class="custom-card custom-card-warning">
                <p style="margin: 0;">⚠️ 未获取到数据源信息，请检查后端服务是否启动</p>
            </div>
            """, unsafe_allow_html=True)
elif page == "资金流向":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">💰 资金流向</h3>
        <p style="color: #666; margin-top: 5px;">Analyze capital flow for individual stocks</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        ff_code = st.text_input("股票代码", value="600519", key="ff_code")
        ff_mode = st.selectbox("Mode", ["minute", "daily"], key="ff_mode")
    with col2:
        if ff_code:
            with st.spinner("Loading fund flow data..."):
                ff_resp = safe_api(f"/api/fund-flow/{ff_code}?mode={ff_mode}")

            if ff_resp and ff_resp.get("data"):
                ff_df = pd.DataFrame(ff_resp["data"])
                ff_df["date"] = pd.to_datetime(ff_df.get("date", ff_df.get("time", ff_df.index)))
                ff_df = ff_df.sort_values("date")

                # Summary metrics
                if "main_net" in ff_df.columns:
                    total_main = ff_df["main_net"].sum()
                    total_large = ff_df["large_net"].sum() if "large_net" in ff_df.columns else 0
                    mcol1, mcol2 = st.columns(2)
                    mcol1.metric("主力净流入", f"{total_main:,.0f}")
                    mcol2.metric("大单净流入", f"{total_large:,.0f}")

                if ff_mode == "minute" and "main_net" in ff_df.columns:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=ff_df["date"], y=ff_df["main_net"],
                        mode="lines", name="主力净流入",
                        line=dict(color="#3498db", width=2)
                    ))
                    fig.update_layout(
                        title="主力净流入（分时）",
                        xaxis_title="Time", yaxis_title="Amount",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                elif ff_mode == "daily" and "main_net" in ff_df.columns:
                    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in ff_df["main_net"]]
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=ff_df["date"], y=ff_df["main_net"],
                        name="主力净流入", marker_color=colors
                    ))
                    fig.update_layout(
                        title="主力净流入（近30日）",
                        xaxis_title="Date", yaxis_title="Amount",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Detail Data")
                st.dataframe(ff_df, use_container_width=True, hide_index=True)
            else:
                st.warning("暂无资金流向数据 available")

elif page == "北向资金":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🧭 北向资金</h3>
        <p style="color: #666; margin-top: 5px;">沪股通 + 深股通 实时资金流向</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading northbound data..."):
        nb_resp = safe_api("/api/northbound")

    if nb_resp and nb_resp.get("data"):
        nb_df = pd.DataFrame(nb_resp["data"])
        nb_df["date"] = pd.to_datetime(nb_df.get("date", nb_df.index))
        nb_df = nb_df.sort_values("date")

        # Summary metrics
        hgt_col = "hgt_yi" if "hgt_yi" in nb_df.columns else nb_df.columns[1]
        sgt_col = "sgt_yi" if "sgt_yi" in nb_df.columns else nb_df.columns[2]

        hgt_latest = nb_df[hgt_col].iloc[-1] if len(nb_df) > 0 else 0
        sgt_latest = nb_df[sgt_col].iloc[-1] if len(nb_df) > 0 else 0
        total_latest = hgt_latest + sgt_latest

        mcol1, mcol2, mcol3 = st.columns(3)
        hgt_color = "#2ecc71" if hgt_latest >= 0 else "#e74c3c"
        sgt_color = "#2ecc71" if sgt_latest >= 0 else "#e74c3c"
        total_color = "#2ecc71" if total_latest >= 0 else "#e74c3c"
        mcol1.metric("沪股通最新", f"{hgt_latest:,.2f} 亿")
        mcol2.metric("深股通最新", f"{sgt_latest:,.2f} 亿")
        mcol3.metric("合计", f"{total_latest:,.2f} 亿")

        # Line chart with two traces
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=nb_df["date"], y=nb_df[hgt_col],
            mode="lines", name="沪股通",
            line=dict(color="#2ecc71", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=nb_df["date"], y=nb_df[sgt_col],
            mode="lines", name="深股通",
            line=dict(color="#3498db", width=2)
        ))
        fig.update_layout(
            title="北向资金流向",
            xaxis_title="Date", yaxis_title="Amount (Yi)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Detail Data")
        st.dataframe(nb_df, use_container_width=True, hide_index=True)
    else:
        st.warning("暂无北向资金数据")

elif page == "龙虎榜":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🐉 龙虎榜</h3>
        <p style="color: #666; margin-top: 5px;">View dragon-tiger board data (top movers)</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        dt_code = st.text_input("股票代码（可选）", value="", key="dt_code")
    with col2:
        dt_start = st.date_input("Start Date", key="dt_start")
    with col3:
        dt_end = st.date_input("End Date", key="dt_end")

    params = []
    if dt_code.strip():
        params.append(f"code={dt_code.strip()}")
    if dt_start:
        params.append(f"start_date={dt_start.strftime('%Y-%m-%d')}")
    if dt_end:
        params.append(f"end_date={dt_end.strftime('%Y-%m-%d')}")
    query = "?" + "&".join(params) if params else ""

    with st.spinner("Loading dragon-tiger data..."):
        dt_resp = safe_api(f"/api/dragon-tiger{query}")

    if dt_resp and dt_resp.get("data"):
        dt_df = pd.DataFrame(dt_resp["data"])

        # Show net_buy as colored metric if available
        if "net_buy" in dt_df.columns:
            total_net = dt_df["net_buy"].sum()
            net_color = "#2ecc71" if total_net >= 0 else "#e74c3c"
            st.markdown(f"""
            <div class="custom-card" style="border-left-color: {net_color};">
                <h4 style="margin: 0;">总净买入</h4>
                <p style="margin: 5px 0 0 0; font-size: 1.5em; color: {net_color}; font-weight: bold;">
                    {total_net:,.0f}
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 龙虎榜数据")
        st.dataframe(dt_df, use_container_width=True, hide_index=True)
    else:
        st.warning("暂无龙虎榜数据")

elif page == "行业排名":
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin: 0; color: #1e3a5f;">🏭 行业排名</h3>
        <p style="color: #666; margin-top: 5px;">查看行业板块涨跌排名</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("加载行业排名数据..."):
        ind_resp = safe_api("/api/industry?top_n=20")

    if ind_resp and ind_resp.get("data"):
        ind_df = pd.DataFrame(ind_resp["data"])

        if "change_pct" in ind_df.columns:
            # Top industries (positive change)
            top_df = ind_df[ind_df["change_pct"] > 0].head(10)
            # Bottom industries (negative change)
            bottom_df = ind_df[ind_df["change_pct"] < 0].sort_values("change_pct").head(10)

            col_top, col_bottom = st.columns(2)

            with col_top:
                st.markdown("### Top Industries")
                for _, row in top_df.iterrows():
                    领涨股 = row.get("领涨股", row.get("领涨股_name", "N/A"))
                    st.markdown(f"""
                    <div class="custom-card" style="border-left-color: #2ecc71;">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <h4 style="margin: 0;">{row.get('name', row.get('industry', 'N/A'))}</h4>
                                <p style="margin: 3px 0 0 0; color: #666; font-size: 0.9em;">领涨股: {领涨股}</p>
                            </div>
                            <div style="color: #2ecc71; font-weight: bold; font-size: 1.2em;">
                                +{row['change_pct']:.2f}%
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_bottom:
                st.markdown("### Bottom Industries")
                for _, row in bottom_df.iterrows():
                    领涨股 = row.get("领涨股", row.get("领涨股_name", "N/A"))
                    st.markdown(f"""
                    <div class="custom-card" style="border-left-color: #e74c3c;">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <h4 style="margin: 0;">{row.get('name', row.get('industry', 'N/A'))}</h4>
                                <p style="margin: 3px 0 0 0; color: #666; font-size: 0.9em;">领涨股: {领涨股}</p>
                            </div>
                            <div style="color: #e74c3c; font-weight: bold; font-size: 1.2em;">
                                {row['change_pct']:.2f}%
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("### Full Ranking Data")
        st.dataframe(ind_df, use_container_width=True, hide_index=True)
    else:
        st.warning("暂无行业排名数据")
