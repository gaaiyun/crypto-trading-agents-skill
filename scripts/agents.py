"""加密货币多 agent 分析系统。

三个独立 agent：

1. ``TechnicalAgent`` —— 纯规则 + 指标：RSI / MACD / SMA20 vs SMA50 / 布林带 z-score
   返回 -1（强卖）到 +1（强买）的分数 + 各指标值
2. ``SentimentAgent`` —— LLM 驱动，对一段新闻 / 推文文本打 -1..+1 情感分。
   没 LLM key 时退化为纯关键词词典 + 平均（保证离线可用）
3. ``RiskAgent`` —— 综合两 agent 信号，给最终建议 + 仓位 + 止损价

v1 的 ``trading_system.py`` 把 sentiment 写死成 0.65；v2 改成可调 / 可测的真实推断。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

import numpy as np
import pandas as pd

from .llm_client import LLMClient, LLMNotAvailable


Signal = Literal["BUY", "SELL", "NEUTRAL"]


# --- 共用工具 ----------------------------------------------------------------

def _signal_from_score(score: float, threshold: float = 0.2) -> Signal:
    if score > threshold:
        return "BUY"
    if score < -threshold:
        return "SELL"
    return "NEUTRAL"


# --- TechnicalAgent ----------------------------------------------------------

@dataclass
class TechnicalReport:
    score: float                       # -1 强卖 ~ +1 强买
    signal: Signal
    rsi: float
    sma_short: float
    sma_long: float
    macd: float
    macd_signal: float
    bb_zscore: float                   # 布林带位置：>2 偏高 <-2 偏低
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: float(v) if isinstance(v, (int, float, np.floating))
                else v for k, v in self.__dict__.items()}


class TechnicalAgent:
    def __init__(self, sma_short: int = 20, sma_long: int = 50,
                 rsi_period: int = 14, bb_period: int = 20):
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.rsi_period = rsi_period
        self.bb_period = bb_period

    def analyze(self, prices: pd.Series) -> TechnicalReport:
        if len(prices) < max(self.sma_long, self.bb_period, self.rsi_period) + 2:
            # 数据不足：给中性
            return TechnicalReport(score=0, signal="NEUTRAL",
                                   rsi=50, sma_short=0, sma_long=0,
                                   macd=0, macd_signal=0, bb_zscore=0,
                                   reasons=["数据不足"])

        # 1. SMA 趋势
        sma_short = prices.rolling(self.sma_short).mean().iloc[-1]
        sma_long = prices.rolling(self.sma_long).mean().iloc[-1]
        sma_score = float(np.sign(sma_short - sma_long))    # +1 或 -1

        # 2. RSI
        rsi = self._calc_rsi(prices, self.rsi_period)
        # RSI 14 < 30 看多反转，> 70 看空反转
        if rsi < 30:
            rsi_score = 0.6
        elif rsi > 70:
            rsi_score = -0.6
        else:
            rsi_score = (50 - rsi) / 80    # ~[-0.25, +0.25]

        # 3. MACD
        macd, macd_signal_val = self._calc_macd(prices)
        macd_score = float(np.sign(macd - macd_signal_val)) * 0.5

        # 4. 布林带 z-score
        rolling_mean = prices.rolling(self.bb_period).mean().iloc[-1]
        rolling_std = prices.rolling(self.bb_period).std().iloc[-1]
        current = prices.iloc[-1]
        bb_z = (current - rolling_mean) / rolling_std if rolling_std > 0 else 0
        # 偏离均线远 → 反转
        bb_score = -float(np.clip(bb_z, -2, 2)) / 2 * 0.5     # ~[-0.5, +0.5]

        # 综合（权重之和 = 1）
        score = (
            0.3 * sma_score +
            0.3 * rsi_score +
            0.2 * macd_score +
            0.2 * bb_score
        )
        score = float(np.clip(score, -1, 1))

        reasons = []
        if sma_score > 0:
            reasons.append(f"SMA{self.sma_short} > SMA{self.sma_long}（趋势向上）")
        elif sma_score < 0:
            reasons.append(f"SMA{self.sma_short} < SMA{self.sma_long}（趋势向下）")
        if rsi < 30:
            reasons.append(f"RSI={rsi:.1f}（超卖）")
        elif rsi > 70:
            reasons.append(f"RSI={rsi:.1f}（超买）")
        if abs(bb_z) > 1.5:
            reasons.append(f"布林带 z={bb_z:.2f}（偏离均值）")
        if not reasons:
            reasons.append("指标偏中性")

        return TechnicalReport(
            score=score, signal=_signal_from_score(score),
            rsi=float(rsi), sma_short=float(sma_short), sma_long=float(sma_long),
            macd=float(macd), macd_signal=float(macd_signal_val),
            bb_zscore=float(bb_z), reasons=reasons,
        )

    @staticmethod
    def _calc_rsi(prices: pd.Series, period: int = 14) -> float:
        delta = prices.diff().dropna()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        if loss.iloc[-1] <= 1e-12:
            return 100.0
        rs = gain.iloc[-1] / loss.iloc[-1]
        return float(100 - 100 / (1 + rs))

    @staticmethod
    def _calc_macd(prices: pd.Series, fast: int = 12, slow: int = 26,
                   signal: int = 9) -> tuple[float, float]:
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return float(macd.iloc[-1]), float(signal_line.iloc[-1])


# --- SentimentAgent ----------------------------------------------------------

@dataclass
class SentimentReport:
    score: float                       # -1 极负 ~ +1 极正
    signal: Signal
    n_inputs: int
    backend: str
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# 简单关键词词典：无 LLM key 时的离线回退
_POSITIVE_KW = [
    "bullish", "surge", "rally", "moon", "breakout", "adoption",
    "etf", "approval", "partnership", "milestone", "all-time high", "ath",
    "看涨", "突破", "利好", "上涨", "牛市", "新高",
]
_NEGATIVE_KW = [
    "bearish", "crash", "dump", "hack", "exploit", "sell-off", "lawsuit",
    "ban", "regulation", "fud", "rugpull", "delisting",
    "看跌", "暴跌", "利空", "抛售", "黑客", "禁令", "下跌", "熊市",
]


class SentimentAgent:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client

    def analyze(self, headlines: List[str], ticker: Optional[str] = None
                ) -> SentimentReport:
        if not headlines:
            return SentimentReport(score=0, signal="NEUTRAL", n_inputs=0,
                                   backend="empty", reasons=["无新闻输入"])

        if self.llm_client and self.llm_client.is_available():
            try:
                return self._analyze_llm(headlines, ticker)
            except LLMNotAvailable:
                pass  # fallback below
        return self._analyze_keyword(headlines)

    def _analyze_keyword(self, headlines: List[str]) -> SentimentReport:
        scores = []
        for h in headlines:
            text = h.lower()
            pos = sum(1 for kw in _POSITIVE_KW if kw in text)
            neg = sum(1 for kw in _NEGATIVE_KW if kw in text)
            total = pos + neg
            if total == 0:
                scores.append(0)
            else:
                scores.append((pos - neg) / total)
        mean = float(np.mean(scores)) if scores else 0
        return SentimentReport(
            score=float(np.clip(mean, -1, 1)),
            signal=_signal_from_score(mean),
            n_inputs=len(headlines), backend="keyword",
            reasons=["关键词字典法（offline fallback）"],
        )

    def _analyze_llm(self, headlines: List[str], ticker: Optional[str]
                     ) -> SentimentReport:
        import json
        system = (
            "你是一名加密货币市场情绪分析师。给定一组新闻标题或推文，"
            "判断市场情绪。只输出 JSON，字段：score (float -1.0 ~ +1.0)、"
            "label (positive/negative/neutral)、reason (≤80 字)。"
        )
        user = (
            f"目标币种：{ticker or '通用市场'}\n\n"
            f"待分析输入（共 {len(headlines)} 条）：\n"
            + "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
            + "\n\n按 system 要求输出 JSON。"
        )
        raw = self.llm_client.chat(system, user, temperature=0.1)
        # 抽 JSON
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            # LLM 没出合规 JSON → 退化为关键词
            return self._analyze_keyword(headlines)
        score = float(data.get("score", 0))
        reason = str(data.get("reason", ""))
        return SentimentReport(
            score=float(np.clip(score, -1, 1)),
            signal=_signal_from_score(score),
            n_inputs=len(headlines),
            backend=f"llm:{self.llm_client.backend}",
            reasons=[reason] if reason else ["LLM 推理"],
        )


# --- RiskAgent ----------------------------------------------------------------

@dataclass
class RiskRecommendation:
    action: Signal
    confidence: float                  # 0 ~ 1
    position_pct: float                # 0 ~ 100 建议仓位百分比
    stop_loss_price: float             # 建议止损价（绝对值）
    take_profit_price: float           # 建议止盈价（绝对值）
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class RiskAgent:
    def __init__(self, max_position_pct: float = 20.0,
                 stop_loss_atr_mult: float = 2.0):
        self.max_position_pct = max_position_pct
        self.stop_loss_atr_mult = stop_loss_atr_mult

    def decide(self, technical: TechnicalReport, sentiment: SentimentReport,
               current_price: float,
               sentiment_weight: float = 0.4) -> RiskRecommendation:
        # 综合分数
        tech_weight = 1 - sentiment_weight
        combined = tech_weight * technical.score + sentiment_weight * sentiment.score
        combined = float(np.clip(combined, -1, 1))

        action = _signal_from_score(combined, threshold=0.15)
        # 置信度：取两 agent 分数绝对值的平均
        confidence = (abs(technical.score) + abs(sentiment.score)) / 2

        # 仓位：分数越极端、置信度越高 → 仓位越大
        position_pct = min(self.max_position_pct * abs(combined), self.max_position_pct)

        # 止损：买入时低于当前价 5%，卖出时高于 5%
        if action == "BUY":
            stop_loss = current_price * 0.95
            take_profit = current_price * 1.10
        elif action == "SELL":
            stop_loss = current_price * 1.05
            take_profit = current_price * 0.90
        else:
            stop_loss = current_price
            take_profit = current_price

        reasons = [
            f"技术面 {technical.signal}（{technical.score:+.2f}）",
            f"情绪面 {sentiment.signal}（{sentiment.score:+.2f}），权重 {sentiment_weight}",
            f"综合分 {combined:+.2f} → {action}",
        ]

        return RiskRecommendation(
            action=action, confidence=float(confidence),
            position_pct=float(position_pct),
            stop_loss_price=float(stop_loss),
            take_profit_price=float(take_profit),
            reasons=reasons,
        )
