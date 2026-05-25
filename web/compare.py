import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import httpx
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="回测对比", layout="wide", page_icon="📊")

st.title("📊 策略回测对比")

if "backtest_data" not in st.session_state:
    st.session_state.backtest_data = []

# Load existing data
if st.session_state.backtest_data:
    st.markdown("### 已保存的回测结果")
    for i, data in enumerate(st.session_state.backtest_data):
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.text(f"{i+1}. {data.get('name', 'Unnamed')}")
        col2.text(f"收益率：{data.get('total_return', 'N/A')}")
        if col3.button("删除", key=f"del_{i}"):
            st.session_state.backtest_data.pop(i)
            st.rerun()

# Form to add new backtest
with st.form("add_backtest"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("回测名称", "MA 策略")
        codes = st.text_input("股票代码", "000001,600519")
        start = st.text_input("开始日期", "20230101")
    with col2:
        end = st.text_input("结束日期", "20251231")
        capital = st.number_input("初始资金", value=1000000.0)
    
    submitted = st.form_submit_button("运行并保存")

if submitted:
    payload = {
        "strategy": "ma_cross",
        "codes": [c.strip() for c in codes.split(",") if c.strip()],
        "start": start,
        "end": end,
        "initial_capital": float(capital),
        "params": {"fast_period": 5, "slow_period": 20}
    }
    
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{API_BASE}/api/backtest",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        
        st.session_state.backtest_data.append({
            "name": name,
            "data": resp
        })
        st.success(f"已保存：{name}")
        st.rerun()
    except Exception as e:
        st.error(f"运行失败：{e}")

# Display comparison if data exists
if st.session_state.backtest_data:
    st.markdown("### 回测对比")
    
    # Create comparison table
    comp_data = []
    for item in st.session_state.backtest_data:
        metrics = item.get("data", {}).get("metrics", {})
        comp_data.append({
            "名称": item.get("name"),
            "最终资产": item.get("data", {}).get("final_capital", 0),
            "总收益率": item.get("data", {}).get("total_return", "N/A"),
            "夏普比率": metrics.get("夏普比率", "N/A"),
            "最大回撤": metrics.get("最大回撤", "N/A"),
            "胜率": metrics.get("胜率", "N/A"),
            "交易次数": len(item.get("data", {}).get("trades", []))
        })
    
    comp_df = pd.DataFrame(comp_data)
    st.dataframe(comp_df, use_container_width=True)
    
    # Plot equity curves comparison
    st.markdown("### 资金曲线对比")
    fig = go.Figure()
    for item in st.session_state.backtest_data:
        equity = item.get("data", {}).get("equity_curve", [])
        if equity:
            edf = pd.DataFrame(equity)
            edf["date"] = pd.to_datetime(edf["date"])
            name = item.get("name", "Unknown")
            fig.add_trace(go.Scatter(
                x=edf["date"], y=edf["value"],
                mode="lines", name=name,
                line=dict(width=2)
            ))
    fig.update_layout(height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("暂无回测数据，请在表单中运行回测")
