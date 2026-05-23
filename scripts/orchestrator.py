"""把三个 agent 串起来产出最终分析报告。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from .agents import (
    RiskAgent,
    RiskRecommendation,
    SentimentAgent,
    SentimentReport,
    TechnicalAgent,
    TechnicalReport,
)
from .llm_client import LLMClient


@dataclass
class AnalysisReport:
    ticker: str
    current_price: float
    technical: TechnicalReport
    sentiment: SentimentReport
    recommendation: RiskRecommendation
    timestamp: str = ""
    data_source: str = ""

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "current_price": float(self.current_price),
            "timestamp": self.timestamp,
            "data_source": self.data_source,
            "technical": self.technical.to_dict(),
            "sentiment": self.sentiment.to_dict(),
            "recommendation": self.recommendation.to_dict(),
        }


class Orchestrator:
    """把 ticker + 价格序列 + 新闻喂入，跑三个 agent，返回最终报告。"""

    def __init__(self,
                 technical_agent: Optional[TechnicalAgent] = None,
                 sentiment_agent: Optional[SentimentAgent] = None,
                 risk_agent: Optional[RiskAgent] = None,
                 llm_client: Optional[LLMClient] = None):
        self.technical_agent = technical_agent or TechnicalAgent()
        self.sentiment_agent = sentiment_agent or SentimentAgent(llm_client=llm_client)
        self.risk_agent = risk_agent or RiskAgent()

    def analyze(self, ticker: str, prices: pd.Series,
                headlines: Optional[List[str]] = None,
                sentiment_weight: float = 0.4,
                data_source: str = "") -> AnalysisReport:
        if prices is None or len(prices) == 0:
            raise ValueError("prices 不能为空")
        current_price = float(prices.iloc[-1])
        technical = self.technical_agent.analyze(prices)
        sentiment = self.sentiment_agent.analyze(headlines or [], ticker=ticker)
        recommendation = self.risk_agent.decide(
            technical, sentiment, current_price=current_price,
            sentiment_weight=sentiment_weight,
        )
        return AnalysisReport(
            ticker=ticker, current_price=current_price,
            technical=technical, sentiment=sentiment,
            recommendation=recommendation,
            timestamp=pd.Timestamp.now().isoformat(),
            data_source=data_source,
        )


def render_markdown(report: AnalysisReport) -> str:
    """报告渲染成 Markdown，给 CLI / 文件输出用。"""
    rec = report.recommendation
    tech = report.technical
    sent = report.sentiment
    lines = [
        f"# {report.ticker} 加密分析报告",
        "",
        f"- 当前价格：${report.current_price:,.2f}",
        f"- 时间戳：{report.timestamp}",
        f"- 数据源：{report.data_source or '未知'}",
        "",
        "## 最终建议",
        "",
        f"- **{rec.action}**（置信度 {rec.confidence:.0%}）",
        f"- 建议仓位：{rec.position_pct:.1f}%",
        f"- 止损价：${rec.stop_loss_price:,.2f}",
        f"- 止盈价：${rec.take_profit_price:,.2f}",
        "",
        "## 技术分析",
        "",
        f"- 信号：{tech.signal}（分数 {tech.score:+.2f}）",
        f"- RSI: {tech.rsi:.1f}",
        f"- SMA{20}: ${tech.sma_short:,.2f}",
        f"- SMA{50}: ${tech.sma_long:,.2f}",
        f"- MACD: {tech.macd:+.4f} / 信号线 {tech.macd_signal:+.4f}",
        f"- 布林带 z-score: {tech.bb_zscore:+.2f}",
        "",
        "### 技术理由",
        "",
    ]
    for r in tech.reasons:
        lines.append(f"- {r}")
    lines += [
        "",
        "## 情绪分析",
        "",
        f"- 信号：{sent.signal}（分数 {sent.score:+.2f}）",
        f"- 后端：{sent.backend}",
        f"- 输入数：{sent.n_inputs}",
        "",
        "### 情绪理由",
        "",
    ]
    for r in sent.reasons:
        lines.append(f"- {r}")
    lines += ["", "## 风控理由", ""]
    for r in rec.reasons:
        lines.append(f"- {r}")
    return "\n".join(lines)
