"""orchestrator.py 端到端测试。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.agents import SentimentAgent, TechnicalAgent, RiskAgent
from scripts.llm_client import LLMClient
from scripts.orchestrator import AnalysisReport, Orchestrator, render_markdown


def _uptrend_prices(n: int = 80) -> pd.Series:
    return pd.Series([100 + i * 0.3 for i in range(n)])


def _downtrend_prices(n: int = 80) -> pd.Series:
    return pd.Series([200 - i * 0.3 for i in range(n)])


# --- Orchestrator -------------------------------------------------------------

def test_orchestrator_uptrend_no_news_returns_report():
    orch = Orchestrator()
    report = orch.analyze("BTC", _uptrend_prices(), headlines=[])
    assert isinstance(report, AnalysisReport)
    assert report.ticker == "BTC"
    assert report.current_price > 0
    assert report.technical.signal in ("BUY", "SELL", "NEUTRAL")
    assert report.sentiment.signal == "NEUTRAL"  # 空新闻
    assert report.recommendation.action in ("BUY", "SELL", "NEUTRAL")


def test_orchestrator_with_positive_news():
    orch = Orchestrator()
    report = orch.analyze("ETH", _uptrend_prices(), headlines=[
        "ETH rallies past resistance, ETF speculation grows",
        "Bullish breakout confirmed by multiple indicators",
    ])
    assert report.sentiment.score > 0
    assert report.sentiment.backend == "keyword"


def test_orchestrator_raises_on_empty_prices():
    orch = Orchestrator()
    with pytest.raises(ValueError):
        orch.analyze("BTC", pd.Series([]))


def test_orchestrator_to_dict_serializable():
    import json
    orch = Orchestrator()
    report = orch.analyze("BTC", _uptrend_prices(), headlines=["bullish"])
    d = report.to_dict()
    # 嵌套结构里有 List[str] 的 reasons 字段
    s = json.dumps(d, ensure_ascii=False, default=str)
    assert "BTC" in s
    assert "recommendation" in d
    assert "technical" in d
    assert "sentiment" in d


def test_orchestrator_with_mocked_llm():
    """LLM 给负面情绪 + 价格也下跌 → 最终 SELL。"""
    llm = LLMClient(backend="deepseek", api_key="sk-test")
    llm.chat = MagicMock(return_value='{"score": -0.9, "label": "negative", "reason": "崩盘"}')
    orch = Orchestrator(llm_client=llm)
    report = orch.analyze("BTC", _downtrend_prices(),
                          headlines=["any text"], sentiment_weight=0.5)
    assert report.sentiment.score == -0.9
    assert report.recommendation.action == "SELL"


def test_orchestrator_custom_agents():
    """传入自定义参数的 agents 应该被尊重。"""
    tech = TechnicalAgent(sma_short=5, sma_long=10)
    sent = SentimentAgent()
    risk = RiskAgent(max_position_pct=10.0)
    orch = Orchestrator(technical_agent=tech, sentiment_agent=sent, risk_agent=risk)
    report = orch.analyze("BTC", _uptrend_prices(), headlines=[])
    # max position 限制生效
    assert report.recommendation.position_pct <= 10.0


# --- render_markdown ---------------------------------------------------------

def test_render_markdown_contains_all_sections():
    orch = Orchestrator()
    report = orch.analyze("BTC", _uptrend_prices(), headlines=["bullish news"])
    md = render_markdown(report)
    assert "# BTC 加密分析报告" in md
    assert "## 最终建议" in md
    assert "## 技术分析" in md
    assert "## 情绪分析" in md
    assert "## 风控理由" in md


def test_render_markdown_includes_recommendation():
    orch = Orchestrator()
    report = orch.analyze("ETH", _uptrend_prices(), headlines=[])
    md = render_markdown(report)
    assert report.recommendation.action in md
    # 数字格式化
    assert "$" in md
