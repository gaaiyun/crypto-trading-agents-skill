"""agents.py 测试 —— 喂构造好的价格 + 新闻，断言决策。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.agents import (
    RiskAgent,
    RiskRecommendation,
    SentimentAgent,
    SentimentReport,
    TechnicalAgent,
    TechnicalReport,
    _signal_from_score,
)
from scripts.llm_client import LLMClient


# --- _signal_from_score -------------------------------------------------------

def test_signal_threshold_default():
    assert _signal_from_score(0.5) == "BUY"
    assert _signal_from_score(-0.5) == "SELL"
    assert _signal_from_score(0.1) == "NEUTRAL"
    assert _signal_from_score(0) == "NEUTRAL"


def test_signal_custom_threshold():
    assert _signal_from_score(0.4, threshold=0.5) == "NEUTRAL"
    assert _signal_from_score(0.6, threshold=0.5) == "BUY"


# --- TechnicalAgent -----------------------------------------------------------

def test_technical_uptrend_returns_buy():
    """单调上涨 → SMA20 > SMA50 → BUY 倾向。"""
    prices = pd.Series([100 + i * 0.5 for i in range(100)])
    agent = TechnicalAgent()
    report = agent.analyze(prices)
    assert isinstance(report, TechnicalReport)
    # 单调上涨同时也会让 RSI > 70 触发反转扣分；但 SMA + MACD 应足够正
    assert report.sma_short > report.sma_long
    # 最终至少不是 SELL
    assert report.signal != "SELL"


def test_technical_downtrend_pushes_sell():
    prices = pd.Series([200 - i * 0.5 for i in range(100)])
    report = TechnicalAgent().analyze(prices)
    assert report.sma_short < report.sma_long
    # 单调下跌，trend score 强负
    assert report.signal in ("SELL", "NEUTRAL")
    assert report.score < 0


def test_technical_insufficient_data():
    prices = pd.Series([100, 101, 102, 103])
    report = TechnicalAgent().analyze(prices)
    assert report.signal == "NEUTRAL"
    assert "数据不足" in report.reasons[0]


def test_technical_rsi_calculation():
    prices = pd.Series([100 + (-1)**i * 5 for i in range(50)])  # 震荡
    rsi = TechnicalAgent._calc_rsi(prices, 14)
    assert 0 <= rsi <= 100


def test_technical_constant_prices_neutral_rsi():
    """常数价格不应让 RSI 抛除零错误。"""
    # 100 个点足够让 SMA50 + RSI14 + BB20 都算得出
    prices = pd.Series([100.0] * 100)
    report = TechnicalAgent().analyze(prices)
    # 不抛错，能返回有效报告
    assert isinstance(report.rsi, float)
    # 常数价格 → RSI 无下跌，应为 100（avg_loss=0 走 return 100.0 那条）
    assert report.rsi == 100.0


def test_technical_to_dict_serializable():
    import json
    prices = pd.Series([100 + i for i in range(80)])
    report = TechnicalAgent().analyze(prices)
    s = json.dumps({k: v for k, v in report.to_dict().items() if k != "reasons"})
    assert "score" in s


# --- SentimentAgent (keyword fallback) ----------------------------------------

def test_sentiment_keyword_positive_news():
    agent = SentimentAgent()
    headlines = [
        "Bitcoin rallies to new all-time high",
        "ETF approval boosts adoption",
        "Major partnership announced for ETH",
    ]
    report = agent.analyze(headlines)
    assert report.score > 0
    assert report.signal == "BUY"
    assert report.backend == "keyword"
    assert report.n_inputs == 3


def test_sentiment_keyword_negative_news():
    agent = SentimentAgent()
    headlines = [
        "Major exchange hack drains $100M",
        "SEC lawsuit causes massive sell-off",
        "Regulation ban triggers crash",
    ]
    report = agent.analyze(headlines)
    assert report.score < 0
    assert report.signal == "SELL"


def test_sentiment_keyword_mixed_neutral():
    agent = SentimentAgent()
    headlines = ["price moves sideways", "no major news today"]
    report = agent.analyze(headlines)
    assert report.signal == "NEUTRAL"


def test_sentiment_empty_input():
    agent = SentimentAgent()
    report = agent.analyze([])
    assert report.score == 0
    assert report.signal == "NEUTRAL"
    assert report.n_inputs == 0
    assert report.backend == "empty"


def test_sentiment_chinese_keywords():
    agent = SentimentAgent()
    headlines = ["比特币突破新高，看涨情绪浓厚", "市场利好不断"]
    report = agent.analyze(headlines)
    assert report.score > 0


# --- SentimentAgent (LLM mocked) ----------------------------------------------

def _make_mocked_llm(response: str) -> LLMClient:
    c = LLMClient(backend="deepseek", api_key="sk-test")
    c.chat = MagicMock(return_value=response)
    return c


def test_sentiment_llm_parses_valid_json():
    llm = _make_mocked_llm('{"score": 0.7, "label": "positive", "reason": "ETF 利好"}')
    agent = SentimentAgent(llm_client=llm)
    report = agent.analyze(["新闻"], ticker="BTC")
    assert report.score == 0.7
    assert report.signal == "BUY"
    assert "llm" in report.backend


def test_sentiment_llm_handles_code_fence():
    llm = _make_mocked_llm('```json\n{"score": -0.5, "label": "negative", "reason": "暴跌"}\n```')
    agent = SentimentAgent(llm_client=llm)
    report = agent.analyze(["新闻"])
    assert report.score == -0.5


def test_sentiment_llm_falls_back_on_bad_json():
    llm = _make_mocked_llm("LLM 没好好出 JSON")
    agent = SentimentAgent(llm_client=llm)
    report = agent.analyze(["bullish positive news"])
    # 退化到 keyword 法
    assert report.backend == "keyword"


def test_sentiment_llm_unavailable_falls_back():
    llm = LLMClient(backend="deepseek", api_key=None)
    agent = SentimentAgent(llm_client=llm)
    report = agent.analyze(["bullish news"])
    assert report.backend == "keyword"


def test_sentiment_score_clipped_to_minus1_plus1():
    llm = _make_mocked_llm('{"score": 5.0, "label": "positive", "reason": "x"}')
    agent = SentimentAgent(llm_client=llm)
    report = agent.analyze(["x"])
    assert report.score == 1.0  # 截断到 +1


# --- RiskAgent ----------------------------------------------------------------

def _make_tech(score: float, signal: str = None) -> TechnicalReport:
    return TechnicalReport(
        score=score, signal=signal or _signal_from_score(score),
        rsi=50, sma_short=100, sma_long=100, macd=0, macd_signal=0, bb_zscore=0,
    )


def _make_sent(score: float, signal: str = None) -> SentimentReport:
    return SentimentReport(
        score=score, signal=signal or _signal_from_score(score),
        n_inputs=5, backend="keyword",
    )


def test_risk_strong_buy_signal():
    rec = RiskAgent().decide(_make_tech(0.8), _make_sent(0.8), current_price=100)
    assert rec.action == "BUY"
    assert rec.confidence > 0.5
    assert rec.position_pct > 0
    assert rec.stop_loss_price < 100


def test_risk_strong_sell_signal():
    rec = RiskAgent().decide(_make_tech(-0.8), _make_sent(-0.8), current_price=100)
    assert rec.action == "SELL"
    assert rec.stop_loss_price > 100  # 卖空止损在上方


def test_risk_mixed_signals_neutral():
    """技术买 + 情绪卖 → 互相抵消 → NEUTRAL。"""
    rec = RiskAgent().decide(_make_tech(0.5), _make_sent(-0.5), current_price=100)
    # 60% 技术 + 40% 情绪 = 0.3 - 0.2 = 0.1 < threshold 0.15
    assert rec.action == "NEUTRAL"


def test_risk_position_pct_caps_at_max():
    agent = RiskAgent(max_position_pct=15.0)
    rec = agent.decide(_make_tech(1.0), _make_sent(1.0), current_price=100)
    assert rec.position_pct <= 15.0


def test_risk_neutral_no_stop_movement():
    rec = RiskAgent().decide(_make_tech(0), _make_sent(0), current_price=100)
    assert rec.action == "NEUTRAL"
    assert rec.stop_loss_price == 100
    assert rec.take_profit_price == 100


def test_risk_sentiment_weight_extremes():
    """sentiment_weight=1 时完全按情绪决策。"""
    rec = RiskAgent().decide(_make_tech(-0.5), _make_sent(0.8), current_price=100,
                             sentiment_weight=1.0)
    assert rec.action == "BUY"


def test_risk_to_dict_serializable():
    import json
    rec = RiskAgent().decide(_make_tech(0.5), _make_sent(0.5), current_price=100)
    s = json.dumps({k: v for k, v in rec.to_dict().items() if k != "reasons"})
    assert "confidence" in s
