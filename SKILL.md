---
name: crypto-trading-agents
description: 当用户需要加密货币交易分析、多 Agent 投研报告、BTC/ETH 行情分析时使用。基于 CryptoTradingAgents 框架的多代理加密货币交易决策系统。
---

# Crypto Trading Agents Skill

## 1. 什么时候用我？

当用户说：
- "分析 BTC 现在能买吗"
- "ETH 行情分析"
- "生成加密货币投研报告"
- "多 Agent 分析 SOL"
- "CryptoTradingAgents"
- 任何加密货币的交易决策需求

## 2. 我能做什么？

### 多 Agent 协同分析
- **市场分析师** - 技术指标、价格走势、支撑阻力
- **新闻分析师** - 最新加密货币新闻、政策解读
- **社交媒体分析师** - Reddit/Twitter 情绪分析
- **基本面分析师** - 代币经济学、团队、路线图

### 多空辩论机制
- **Bull Researcher** - 看涨论点
- **Bear Researcher** - 看跌论点
- **Debator** - 双方辩论
- **Decision Maker** - 最终决策

### 数据源集成
- **行情数据**: Binance API
- **技术指标**: taapi.io
- **新闻**: CoinDesk、BlockBeats、CoinCap
- **情绪**: Reddit、Fear & Greed Index
- **链上**: Glassnode（可选）

## 3. 使用示例

### 基础用法
```bash
# 分析 BTC
python scripts/run_analysis.py --ticker BTC --date 2026-03-01

# 分析 ETH，使用全部 Agent
python scripts/run_analysis.py --ticker ETH --agents all --depth deep

# 快速分析
python scripts/run_analysis.py --ticker SOL --depth quick
```

### OpenClaw 调用
```python
# 在 OpenClaw 中自动触发
用户："帮我分析 BTC 现在能不能买"
→ 自动调用 crypto-trading-agents skill
→ 生成分析报告
→ 返回建议：买入/卖出/观望 + 置信度
```

### 输出格式
- **Markdown 报告** - 可读性强，适合人工阅读
- **JSON 格式** - 适合程序处理
- **PDF 报告** - 正式文档（可选）

## 4. 配置说明

### 环境变量（references/.env.example）
```bash
# LLM API Keys
DASHSCOPE_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx

# 数据源 API Keys
TAAPI_API_KEY=xxx
COINDESK_API_KEY=xxx
```

### 配置文件（config/default.yaml）
```yaml
llm:
  provider: dashscope
  model: qwen-plus

analysis:
  default_agents:
    - market_analyst
    - news_analyst
    - fundamentals_analyst
  default_depth: medium

output:
  format: markdown
  save_path: ~/.openclaw/workspace/reports/
```

## 5. 报告示例

```markdown
# BTC 分析报告 (2026-03-01)

## 市场分析师
- 当前价格：$95,234
- 24h 变化：+2.3%
- 支撑位：$92,000
- 阻力位：$98,000
- RSI: 58 (中性)

## 新闻分析师
- 正面：SEC 批准新 ETF
- 负面：某交易所被黑
- 中性：美联储利率决议

## 社交媒体情绪
- Reddit: 65% 正面
- Twitter: 72% 正面
- Fear & Greed: 68 (贪婪)

## 基本面分析
- 市值排名：#1
- 24h 交易量：$28B
- 链上活动：活跃

## 多空辩论
### 看涨论点
1. 机构采用加速
2. 减半后供应减少
3. 技术面突破关键阻力

### 看跌论点
1. 宏观不确定性
2. 短期超买
3. 监管风险

## 最终建议
**决策**: 买入（定投）
**置信度**: 72%
**仓位建议**: 5-10%
**止损位**: $88,000
```

## 6. 依赖项

### Python 包
- Python 3.13+
- langgraph
- chromadb
- requests
- pandas
- ta-lib (可选)

### API 服务
- Binance API (免费)
- taapi.io (免费 tier)
- CoinDesk API (免费)
- Reddit API (免费)

## 7. 注意事项

1. **投资建议免责声明**: 本报告仅供参考，不构成投资建议
2. **API 限流**: 部分数据源有调用限制
3. **数据延迟**: 实时数据可能有 1-5 分钟延迟
4. **LLM 成本**: 深度分析消耗较多 Token

## 8. 故障排除

### 常见问题
- **API Key 错误**: 检查 .env 文件配置
- **数据获取失败**: 检查网络连接
- **报告生成失败**: 检查磁盘空间
- **LLM 超时**: 增加 timeout 参数

### 日志位置
- `~/.openclaw/workspace/logs/crypto-agents.log`

---

_基于 [CryptoTradingAgents](https://github.com/Tomortec/CryptoTradingAgents) 二次开发_
_原项目基于 arXiv 2412.20138 论文_
