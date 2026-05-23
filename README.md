# crypto-trading-agents-skill

加密货币多 agent 分析：技术 + 情绪（LLM 或关键词字典）+ 风控 → 一份给定币种的完整建议报告。

灵感来自 [CryptoTradingAgents](https://github.com/Tomortec/CryptoTradingAgents)，但本仓库不依赖那个框架 —— 整套 agent 链路自包含、可单测、不需要 OpenClaw 平台。

## v2 三层 agent 架构

| Agent | 输入 | 输出 |
|---|---|---|
| `TechnicalAgent` | 价格序列（pandas Series） | 综合分数 (-1..+1) + RSI / SMA20-50 / MACD / 布林带 z-score |
| `SentimentAgent` | 一组新闻标题或推文 | 情绪分 (-1..+1) + 信号 (BUY/SELL/NEUTRAL) |
| `RiskAgent` | 上面两个 agent 的输出 + 当前价 | action / 置信度 / 仓位百分比 / 止损价 / 止盈价 |

情绪 agent 优先用 LLM（openai / anthropic / deepseek 任一），缺 key 时**优雅退化**到关键词字典法（中英文双语词典都内置），保证离线场景下也有合理输出 —— 不像 v1 直接 hardcode `score = 0.65`。

## 安装

```bash
pip install -r requirements.txt
# 想用 LLM 情绪分析：
pip install openai      # openai / deepseek backend
pip install anthropic   # anthropic backend
# 然后设 OPENAI_API_KEY / DEEPSEEK_API_KEY / ANTHROPIC_API_KEY
```

## 快速开始

```bash
# 离线 demo（合成数据 + 关键词情绪，无任何 API key）
python __main__.py analyze BTC --synthetic

# 真实数据（CoinGecko 免费 API，无需 key）
python __main__.py analyze ETH --days 90

# 带新闻文本（一行一条）
python __main__.py analyze SOL --days 60 \
    --headlines news.txt \
    --output-format json -o report.json

# 启用 LLM 情绪分析（需要 DEEPSEEK_API_KEY）
python __main__.py analyze BTC --days 90 \
    --headlines news.txt --use-llm --backend deepseek

# 单独抓当前价 + 24h 数据
python __main__.py fetch BTC

# 看可用 LLM backend 状态
python __main__.py list-models
```

## 库调用

```python
import pandas as pd
from scripts.data_fetch import fetch_ohlcv_coingecko, fetch_recent_market_data
from scripts.orchestrator import Orchestrator, render_markdown
from scripts.llm_client import LLMClient

df = fetch_ohlcv_coingecko("BTC", days=90)
snap = fetch_recent_market_data("BTC")
df.iloc[-1, df.columns.get_loc("price")] = snap.current_price

orch = Orchestrator(llm_client=LLMClient(backend="deepseek"))
report = orch.analyze(
    ticker="BTC",
    prices=df["price"],
    headlines=[
        "Bitcoin breaks resistance",
        "Major ETF approval expected",
    ],
    sentiment_weight=0.4,
)
print(render_markdown(report))
print(f"决策: {report.recommendation.action} @ 置信 {report.recommendation.confidence:.0%}")
```

## 一个真实输出（mixed 信号示例）

```
# BTC 加密分析报告

- 当前价格：$56,154.15
- 数据源：synthetic

## 最终建议
- **NEUTRAL**（置信度 52%）
- 建议仓位：0.9%
- 止损价：$56,154.15
- 止盈价：$56,154.15

## 技术分析
- 信号：SELL（分数 -0.37）
- RSI: 44.8 | SMA20: $56,336.01 | SMA50: $57,593.90
- MACD: -630.5166 / 信号线 -463.5612
- 布林带 z-score: -0.14

## 情绪分析
- 信号：BUY（分数 +0.67）
- 后端：keyword
- 输入：3 条标题

## 风控理由
- 技术面 SELL（-0.37）
- 情绪面 BUY（+0.67），权重 0.4
- 综合分 -0.02 → NEUTRAL
```

技术面看空 + 情绪面看多 → 风控**老老实实给 NEUTRAL** 而不是逼自己挑边。这是 v2 想做的事 —— 多 agent 真在打架时，把"打架"暴露给用户，别强行综合出一个假的决断。

## 设计取舍

- **数据源用 CoinGecko 免费 API**：不需要 API key，每分钟 ~50 次足够人类用。
  生产场景可换 Binance / Kraken / Coinbase 的官方 API。
- **TechnicalAgent 权重写死**：SMA 30% + RSI 30% + MACD 20% + 布林带 20%。这是
  纯启发式，没有数据驱动调参。要调参建议自己继承类改 weights。
- **SentimentAgent LLM 失败时退化关键词**：而不是 raise —— 因为分析报告里只要
  情绪是某一项输入，没情绪也不该让整个 pipeline 崩。
- **RiskAgent 止损止盈固定 5% / 10%**：v1 模板的做法。要按 ATR 动态调，自己继承。
- **没接实盘下单**：本仓库只产报告。要下单接 ccxt 或 lumibot。

## 项目结构

```
crypto-trading-agents-skill/
├── __main__.py                  # CLI：analyze / fetch / list-models
├── scripts/
│   ├── llm_client.py            # 三 backend LLM 客户端
│   ├── data_fetch.py            # CoinGecko + 合成数据
│   ├── agents.py                # Technical / Sentiment / Risk 三 agent
│   ├── orchestrator.py          # 串三个 agent + 渲染 markdown
│   ├── run_analysis.py          # v1 legacy CLI（保留）
│   └── trading_system.py        # v1 fake-sentiment 实现（保留对比）
├── tests/                       # 56 个测试，全部 mock，不联网
├── config/default.yaml
└── requirements.txt
```

## 测试

```bash
pip install pytest
pytest tests/ -v
```

56 个测试，130ms 跑完。LLM 全部 mock，CoinGecko HTTP 全部 mock，全程不联网。

## 已知限制

- TechnicalAgent 单调上涨数据上会触发 RSI > 70 扣分 —— 这是设计意图（"涨太多了要反转"），但短期强趋势可能被误判。
- SentimentAgent 关键词词典只有 ~40 词，复杂句式（讽刺、反问）会判错。LLM 路径更可靠但要 API key。
- 风控里仓位计算 = max_position_pct × abs(combined_score)，没接资金管理（Kelly / 波动率适应仓位等）。

## 许可

Apache 2.0
