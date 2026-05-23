---
name: crypto-trading-agents-skill
description: 加密货币多 agent 分析：技术指标 + 新闻情绪（LLM）+ 风控，产出一份给定币种的完整建议报告（含建议、置信度、仓位、止损止盈）。
---

# crypto-trading-agents-skill

## 什么时候用

- "对 BTC / ETH / SOL 做一份多角度分析"
- "把技术面和新闻情绪一起喂给我一个买卖建议"
- "我想看看 LLM 怎么解读这批加密新闻"
- "组个简单的多 agent 协同分析框架"

## 入口

```bash
python __main__.py analyze BTC --days 90 --headlines news.txt --use-llm
python __main__.py analyze ETH --synthetic        # 离线 demo
python __main__.py fetch SOL                       # 当前价 + 24h 数据
python __main__.py list-models                     # LLM backend 配置
```

库调用：

- `scripts.orchestrator::Orchestrator.analyze(ticker, prices, headlines, sentiment_weight)`
- `scripts.agents::TechnicalAgent / SentimentAgent / RiskAgent` — 分别独立可用
- `scripts.data_fetch::fetch_ohlcv_coingecko / fetch_recent_market_data`
- `scripts.llm_client::LLMClient(backend="deepseek" | "openai" | "anthropic")`

## 输出字段

```python
report.recommendation       # action, confidence, position_pct, stop_loss_price, take_profit_price
report.technical            # score, rsi, sma_short/long, macd, bb_zscore
report.sentiment            # score, signal, backend (llm:xxx 或 keyword)
```

## 依赖

- 必需：Python 3.10+，pandas + numpy
- 可选 openai / anthropic：LLM 情绪分析；缺时退化关键词字典法
- 可选 CoinGecko 联网（默认）；不能联网就 `--synthetic`

## 注意事项

- 报告是分析建议，不是投资建议。回测前自己核对数据 / 指标 / 时区。
- LLM 情绪可能误判讽刺 / 反问。关键决策不要只看一个信号。
- CoinGecko 免费 API 有速率限制（~50/min），不适合高频。
