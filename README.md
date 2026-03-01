# Crypto Trading Agents Skill

基于 [CryptoTradingAgents](https://github.com/Tomortec/CryptoTradingAgents) 框架的 OpenClaw Skill，提供多 Agent 协同的加密货币交易分析。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd C:\Users\gaaiy\.openclaw\workspace\skills\crypto-trading-agents

# 创建虚拟环境（可选）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install pyyaml python-dotenv requests pandas
```

### 2. 配置 API Key

```bash
# 复制环境变量模板
copy references\.env.example references\.env

# 编辑 .env 文件，填入你的 API Key
# 至少配置一个 LLM API Key（推荐 DASHSCOPE_API_KEY）
```

### 3. 运行分析

```bash
# 分析 BTC
python scripts\run_analysis.py --ticker BTC

# 分析 ETH，深度分析
python scripts\run_analysis.py --ticker ETH --depth deep

# 输出 JSON 格式
python scripts\run_analysis.py --ticker SOL --output json

# 查看详细日志
python scripts\run_analysis.py --ticker BTC -v
```

## 📖 使用说明

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--ticker, -t` | 加密货币代码（必需） | - |
| `--date, -d` | 分析日期 (YYYY-MM-DD) | 今天 |
| `--agents, -a` | Agent 团队配置 | default |
| `--depth` | 分析深度 (quick/medium/deep) | medium |
| `--output, -o` | 输出格式 (markdown/json/pdf) | markdown |
| `--output-dir` | 输出目录 | ~/.openclaw/workspace/reports/ |
| `--config` | 配置文件路径 | config/default.yaml |
| `--non-interactive` | 非交互模式 | False |
| `--verbose, -v` | 详细输出 | False |

### 示例

```bash
# 快速分析 BTC
python scripts\run_analysis.py -t BTC --depth quick

# 深度分析 ETH，输出 JSON
python scripts\run_analysis.py -t ETH --depth deep -o json

# 分析多个币种（批处理）
for ticker in BTC ETH SOL; do
  python scripts\run_analysis.py -t $ticker
done
```

## 🤖 多 Agent 架构

### Agent 角色

| Agent | 职责 |
|-------|------|
| **市场分析师** | 技术指标、价格走势、支撑阻力 |
| **新闻分析师** | 最新加密货币新闻、政策解读 |
| **社交媒体分析师** | Reddit/Twitter 情绪分析 |
| **基本面分析师** | 代币经济学、团队、路线图 |

### 多空辩论机制

```
Bull Researcher → 看涨论点
                    ↓
Bear Researcher → 看跌论点 → Debator → Decision Maker → 最终建议
```

## 📊 输出示例

### Markdown 报告

```markdown
# BTC 分析报告 (2026-03-01)

## 市场分析
- 当前价格：$95,234
- 24h 变化：+2.3%
- 支撑位：$92,000
- 阻力位：$98,000

## 最终建议
**决策**: 买入（定投）
**置信度**: 72%
**仓位建议**: 5-10%
**止损位**: $88,000
```

### JSON 输出

```json
{
  "ticker": "BTC",
  "date": "2026-03-01",
  "recommendation": {
    "action": "BUY",
    "confidence": 72,
    "position": "5-10%",
    "stop_loss": 88000
  }
}
```

## ⚙️ 配置说明

### 配置文件 (config/default.yaml)

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

### 环境变量

```bash
# LLM API Keys
DASHSCOPE_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx

# 数据源 API Keys
TAAPI_API_KEY=xxx
COINDESK_API_KEY=xxx
```

## 📁 项目结构

```
crypto-trading-agents/
├── SKILL.md              # OpenClaw Skill 描述
├── README.md             # 本文档
├── scripts/
│   ├── run_analysis.py   # 主分析脚本
│   └── setup_env.py      # 环境配置脚本
├── config/
│   ├── default.yaml      # 默认配置
│   └── agents.yaml       # Agent 配置
├── references/
│   ├── .env.example      # 环境变量模板
│   └── ...
└── assets/
    └── icon.png          # Skill 图标
```

## 🔧 故障排除

### 常见问题

**Q: API Key 错误**
```
A: 检查 references/.env 文件是否正确配置
```

**Q: 数据获取失败**
```
A: 检查网络连接，确认 API 服务可用
```

**Q: 依赖安装失败**
```
A: 确保 Python 版本 >= 3.13
   python --version
```

### 日志位置

```
~/.openclaw/workspace/logs/crypto-agents.log
```

## 📝 免责声明

⚠️ **本报告仅供参考，不构成投资建议**

加密货币市场风险极高，价格波动剧烈。本工具生成的分析结果基于历史数据和公开信息，不保证准确性或完整性。

请在做出任何投资决策前：
1. 自行研究 (DYOR)
2. 咨询专业理财顾问
3. 只投资你能承受损失的金额

## 🙏 致谢

- 原项目：[CryptoTradingAgents](https://github.com/Tomortec/CryptoTradingAgents)
- 研究论文：[arXiv 2412.20138](https://arxiv.org/pdf/2412.20138)
- Tauric Research 团队

## 📄 许可证

Apache 2.0
