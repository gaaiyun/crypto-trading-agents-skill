"""加密货币价格数据获取。

主用 CoinGecko 公开 API（不需 key，每分钟 ~50 次免费）：
- ``fetch_ohlcv_coingecko(coin_id, vs, days)``：拉 N 天日线 OHLC + 收盘价
- ``fetch_recent_market_data(coin_id, vs)``：当前价 + 24h 涨跌幅 + 成交量

不联网的回退：``synthetic_ohlcv``（合成数据，给测试 / demo 用）。

CoinGecko coin_id 与常见 ticker 的对应：
- BTC → "bitcoin"
- ETH → "ethereum"
- SOL → "solana"
- BNB → "binancecoin"
- XRP → "ripple"
- ADA → "cardano"
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


COIN_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
}


@dataclass
class MarketSnapshot:
    ticker: str
    coin_id: str
    current_price: float
    change_24h_pct: float
    volume_24h: float
    market_cap: float
    source: str = "coingecko"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "coin_id": self.coin_id,
            "current_price": float(self.current_price),
            "change_24h_pct": float(self.change_24h_pct),
            "volume_24h": float(self.volume_24h),
            "market_cap": float(self.market_cap),
            "source": self.source,
        }


def _ticker_to_coin_id(ticker_or_id: str) -> str:
    """规范化：BTC → bitcoin；已经是 coingecko id 时原样返回。"""
    t = ticker_or_id.strip().upper().replace("/USDT", "").replace("/USD", "")
    return COIN_ID_MAP.get(t, ticker_or_id.lower())


def _http_get_json(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-trading-agents-skill/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_recent_market_data(ticker: str, vs: str = "usd") -> MarketSnapshot:
    """从 CoinGecko /simple/price 拉当前价 + 24h 数据。"""
    coin_id = _ticker_to_coin_id(ticker)
    params = urllib.parse.urlencode({
        "ids": coin_id,
        "vs_currencies": vs,
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    })
    url = f"https://api.coingecko.com/api/v3/simple/price?{params}"
    data = _http_get_json(url)
    if coin_id not in data:
        raise RuntimeError(
            f"CoinGecko 没返回 {coin_id} 的数据。原始响应：{data}"
        )
    info = data[coin_id]
    return MarketSnapshot(
        ticker=ticker.upper(),
        coin_id=coin_id,
        current_price=float(info.get(vs, 0)),
        change_24h_pct=float(info.get(f"{vs}_24h_change", 0)),
        volume_24h=float(info.get(f"{vs}_24h_vol", 0)),
        market_cap=float(info.get(f"{vs}_market_cap", 0)),
    )


def fetch_ohlcv_coingecko(ticker: str, vs: str = "usd",
                          days: int = 90) -> pd.DataFrame:
    """从 CoinGecko /market_chart 拉 N 天日线数据。

    返回 DataFrame：index = 时间戳，columns = ['price', 'volume']
    （CoinGecko 不公开 OHLC，但日线收盘价 + 成交量够算大多数指标）
    """
    coin_id = _ticker_to_coin_id(ticker)
    params = urllib.parse.urlencode({
        "vs_currency": vs,
        "days": days,
        "interval": "daily",
    })
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?{params}"
    data = _http_get_json(url)
    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])
    if not prices:
        raise RuntimeError(f"CoinGecko 没返回 {coin_id} 的 market_chart 数据")
    df = pd.DataFrame(prices, columns=["ts_ms", "price"])
    df["volume"] = [v[1] for v in volumes] if volumes else 0
    df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms")
    df = df.set_index("timestamp").drop(columns=["ts_ms"])
    return df


def synthetic_ohlcv(n_days: int = 90, start_price: float = 50_000.0,
                    daily_vol: float = 0.03, seed: int = 42) -> pd.DataFrame:
    """合成日线数据，给测试和 demo 用。"""
    import numpy as np
    rng = np.random.default_rng(seed)
    log_rets = rng.normal(0.001, daily_vol, n_days)
    prices = start_price * np.exp(log_rets.cumsum())
    volumes = rng.uniform(1e8, 5e8, n_days)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_days, freq="D")
    df = pd.DataFrame({"price": prices, "volume": volumes}, index=dates)
    df.index.name = "timestamp"
    return df
