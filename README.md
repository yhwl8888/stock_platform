# 量化选股回测平台

A-share 股票量化回测与选股平台，支持策略回测、选股筛选、模拟交易。

## 技术栈

- **后端**: FastAPI + SQLite
- **前端**: Streamlit + Plotly
- **回测引擎**: 自研事件驱动引擎
- **数据源**: AKShare (在线) / 本地生成 (离线)

## 功能特性

### 1. 策略回测
支持的策略：
- 均线金叉死叉 (ma_cross)
- RSI 超买超卖 (rsi)
- 布林带 (bollinger)
- MACD 指标 (macd)
- EMA 指数均线 (ema_cross)

### 2. 选股筛选
支持的筛选条件：
- 收盘价在均线上方/下方
- 均线金叉
- RSI 区间
- 放量
- KDJ 金叉
- MACD 金叉
- 均线多头排列
- 涨跌幅区间
- 换手率区间
- 价格区间
- 均线趋势
- 成交量金叉

### 3. 模拟交易
- 账户概览
- 下单交易
- 历史记录
- 持仓跟踪

### 4. 数据管理
- 股票数据浏览
- 实时行情查询
- 本地数据存储

## 安装与启动

### 安装依赖

```bash
pip install fastapi uvicorn streamlit plotly pandas numpy pydantic akshare httpx
```

### 启动服务

#### 方式 1: 单命令启动 (推荐)
```bash
cd stock_platform
python run.py
```

#### 方式 2: 分别启动
```bash
# 终端 1: 启动后端
cd stock_platform
python -m uvicorn api.main:app --reload --port 8000

# 终端 2: 启动前端
python -m streamlit run web/app.py --server.port 8501
```

#### 方式 3: PowerShell 脚本
```powershell
cd stock_platform
.\start_all.ps1
```

### 访问地址

- **后端 API**: http://localhost:8000
- **前端界面**: http://localhost:8501

## 使用指南

### 策略回测

1. 进入 "策略回测" 页面
2. 选择策略类型
3. 输入股票代码 (逗号分隔)
4. 设置回测日期范围和初始资金
5. 点击 "运行回测"

### 选股筛选

1. 进入 "选股筛选" 页面
2. 添加筛选条件 (可添加多个)
3. 设置数据日期范围
4. 点击 "开始筛选"
5. 导出结果 (CSV)

### 模拟交易

1. 进入 "模拟交易" 页面
2. 查看账户信息
3. 输入股票代码、方向、价格、数量
4. 提交委托
5. 跟踪持仓和收益

## 数据说明

- **前复权价格**: 所有 K 线数据均为前复权价格
- **数据覆盖**: 2020 年至今的 A 股数据
- **样本股票**: 55 只主流股票 (离线模式)
- **数据更新**: 联网时自动同步最新数据

## 策略参数说明

### MA 交叉策略
- `fast_period`: 快线周期 (默认 5)
- `slow_period`: 慢线周期 (默认 20)

### RSI 策略
- `period`: RSI 计算周期 (默认 14)
- `oversold`: 超卖阈值 (默认 30)
- `overbought`: 超买阈值 (默认 70)

### MACD 策略
- `fast`: 快线周期 (默认 12)
- `slow`: 慢线周期 (默认 26)
- `signal_period`: 信号线周期 (默认 9)

### EMA 交叉策略
- `fast_period`: 快线周期 (默认 12)
- `slow_period`: 慢线周期 (默认 26)

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/stocks` | GET | 获取股票列表 |
| `/api/stock/{code}/daily` | GET | 获取日线数据 |
| `/api/strategies` | GET | 获取策略列表 |
| `/api/backtest` | POST | 运行回测 |
| `/api/screener/filters` | GET | 获取筛选条件 |
| `/api/screener/run` | POST | 运行筛选 |
| `/api/quote/{code}` | GET | 获取实时行情 |
| `/api/paper/account` | GET | 获取账户信息 |
| `/api/paper/order` | POST | 提交委托 |
| `/api/paper/history` | GET | 获取交易历史 |
| `/api/paper/reset` | POST | 重置账户 |

## 注意事项

1. **网络限制**: 当前环境网络受限，使用本地生成数据
2. **价格范围**: 模拟数据价格接近真实基准价，但非实时行情
3. **数据准确性**: 离线模式下仅支持 55 只样本股票
4. **性能优化**: 筛选大行情数据时可能耗时较长

## 开发计划

- [ ] 添加更多技术指标策略
- [ ] 优化数据加载性能
- [ ] 添加回测结果对比功能
- [ ] 添加报告生成
- [ ] 支持更多数据源

## 许可证

MIT License
