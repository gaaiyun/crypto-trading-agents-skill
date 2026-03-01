#!/usr/bin/env python3
"""
Crypto Trading Agents - Multi-agent analysis system
"""

import asyncio
from typing import Dict, List
import pandas as pd
from datetime import datetime


class TechnicalAnalysisAgent:
    """Technical analysis agent"""
    
    def __init__(self):
        self.name = "Technical Analyst"
    
    async def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Perform technical analysis"""
        # Calculate indicators
        data['SMA_20'] = data['close'].rolling(window=20).mean()
        data['SMA_50'] = data['close'].rolling(window=50).mean()
        data['RSI'] = self._calculate_rsi(data['close'])
        
        # Generate signals
        latest = data.iloc[-1]
        signal = "NEUTRAL"
        
        if latest['SMA_20'] > latest['SMA_50'] and latest['RSI'] < 70:
            signal = "BUY"
        elif latest['SMA_20'] < latest['SMA_50'] and latest['RSI'] > 30:
            signal = "SELL"
        
        return {
            'agent': self.name,
            'symbol': symbol,
            'signal': signal,
            'indicators': {
                'SMA_20': float(latest['SMA_20']),
                'SMA_50': float(latest['SMA_50']),
                'RSI': float(latest['RSI'])
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))


class SentimentAnalysisAgent:
    """Sentiment analysis agent"""
    
    def __init__(self):
        self.name = "Sentiment Analyst"
    
    async def analyze(self, symbol: str) -> Dict:
        """Analyze market sentiment"""
        # Simulate sentiment analysis
        sentiment_score = 0.65  # Positive sentiment
        
        if sentiment_score > 0.6:
            signal = "BUY"
        elif sentiment_score < 0.4:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        
        return {
            'agent': self.name,
            'symbol': symbol,
            'signal': signal,
            'sentiment_score': sentiment_score,
            'timestamp': datetime.now().isoformat()
        }


class RiskManagementAgent:
    """Risk management agent"""
    
    def __init__(self):
        self.name = "Risk Manager"
    
    async def analyze(self, symbol: str, signals: List[Dict]) -> Dict:
        """Assess risk and provide recommendation"""
        buy_signals = sum(1 for s in signals if s['signal'] == 'BUY')
        sell_signals = sum(1 for s in signals if s['signal'] == 'SELL')
        
        if buy_signals > sell_signals:
            recommendation = "BUY"
            confidence = buy_signals / len(signals)
        elif sell_signals > buy_signals:
            recommendation = "SELL"
            confidence = sell_signals / len(signals)
        else:
            recommendation = "HOLD"
            confidence = 0.5
        
        return {
            'agent': self.name,
            'symbol': symbol,
            'recommendation': recommendation,
            'confidence': confidence,
            'risk_level': 'MEDIUM',
            'timestamp': datetime.now().isoformat()
        }


class CryptoTradingSystem:
    """Multi-agent crypto trading system"""
    
    def __init__(self):
        self.technical_agent = TechnicalAnalysisAgent()
        self.sentiment_agent = SentimentAnalysisAgent()
        self.risk_agent = RiskManagementAgent()
    
    async def analyze_symbol(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Run multi-agent analysis"""
        # Gather signals from all agents
        technical_result = await self.technical_agent.analyze(symbol, data)
        sentiment_result = await self.sentiment_agent.analyze(symbol)
        
        signals = [technical_result, sentiment_result]
        
        # Risk management decision
        final_decision = await self.risk_agent.analyze(symbol, signals)
        
        return {
            'symbol': symbol,
            'signals': signals,
            'final_decision': final_decision,
            'timestamp': datetime.now().isoformat()
        }


async def main():
    """Example usage"""
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'date': dates,
        'close': [50000 + i * 100 for i in range(100)]
    })
    
    system = CryptoTradingSystem()
    result = await system.analyze_symbol('BTC/USDT', data)
    
    print(f"Analysis for {result['symbol']}:")
    print(f"Final Decision: {result['final_decision']['recommendation']}")
    print(f"Confidence: {result['final_decision']['confidence']:.2%}")


if __name__ == '__main__':
    asyncio.run(main())
