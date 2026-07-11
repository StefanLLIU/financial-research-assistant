# 📈 股票研究助手 · Financial Research Assistant

一个基于 **FastAPI + yfinance** 的股票研究工具，输入股票代码即可获取实时行情、分析师目标价、财报分析、交互式走势图和自动生成的投资评分。支持**中英文切换**。

A stock research web app built with **FastAPI + yfinance**. Enter a ticker to get live price data, analyst targets, earnings analysis, interactive charts, and an auto-generated investment score. Bilingual (中文 / English).

> ⚠️ 本工具仅供学习与研究，所有内容基于公开数据自动生成，**不构成投资建议**。
> For educational use only. Auto-generated from public data; **not investment advice.**

---

## ✨ 功能 · Features

- **实时行情** — 通过 yfinance 获取真实股价、市值、市盈率、52 周高低点
- **分析师目标价** — 显示平均目标价与上涨/下跌空间
- **投资评分** — 1–10 分的看涨 / 中性 / 看跌综合评分，基于价格位置、市盈率、分析师上涨空间和新闻情绪
- **财报分析** — 最新季度 EPS 与营收的实际 vs 预期、超预期百分比、历史季度趋势
- **交互式走势图** — Plotly 绘制，支持 1M / 3M / 1Y / 5Y 时间范围切换
- **热门板块侧边栏** — 15 个可折叠板块（七巨头、半导体、CPO、核电、航天、虚拟币、大盘 ETF、医药、能源、中概股等），一键查询
- **中英文切换** — 右上角一键切换，界面、摘要、评分全部本地化
- **DEMO 模式** — 输入 `DEMO` 使用内置示例数据，无需联网即可体验完整功能
- **数据持久化** — 每次查询结果保存到 SQLite

---

## 🚀 快速开始 · Quick Start

```bash
# 1. 克隆仓库
git clone https://github.com/StefanLLIU/financial-research-assistant.git
cd financial-research-assistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
uvicorn main:app --reload

# 4. 打开浏览器访问
#    http://localhost:8000
```

在输入框输入股票代码（如 `NVDA`、`AAPL`、`TSLA`），或点击右侧板块中的任意股票。想快速体验可以先输入 **`DEMO`**。

---

## 🛠️ 技术栈 · Tech Stack

| 组件 | 用途 |
|------|------|
| [FastAPI](https://fastapi.tiangolo.com/) | Web 框架，服务器端渲染 |
| [yfinance](https://github.com/ranaroussi/yfinance) | 雅虎财经股票数据 |
| [curl_cffi](https://github.com/lexiforest/curl_cffi) | 浏览器指纹模拟，绕过雅虎财经限流 |
| [Plotly.js](https://plotly.com/javascript/) | 交互式价格图表 |
| SQLite | 查询结果持久化 |

---

## 📁 项目结构 · Structure

```
financial-research-assistant/
├── main.py            # FastAPI 应用：数据抓取、评分、财报、图表、路由、UI
├── database.py        # SQLite 持久化层
├── requirements.txt   # 依赖清单
└── README.md
```

---

## 📊 投资评分说明 · Scoring

综合评分（1–10）由以下四个因子加权得出，缺失的因子会自动跳过：

1. **价格位置** — 当前价在 52 周区间中的位置（越低分越高）
2. **市盈率** — 合理区间加分，过高或为负扣分
3. **分析师上涨空间** — 目标价相对现价的上涨/下跌幅度
4. **新闻情绪** — 基于新闻标题关键词的正负面判断

| 分数 | 标签 |
|------|------|
| 7–10 | 🟢 看涨 Bullish |
| 4–6 | ⚪ 中性 Neutral |
| 1–3 | 🔴 看跌 Bearish |

---

## 📝 许可 · License

个人项目，仅供学习。Personal project for educational purposes.
