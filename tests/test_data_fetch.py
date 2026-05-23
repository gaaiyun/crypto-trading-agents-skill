"""data_fetch.py 测试 —— 不发网络请求。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_fetch import (
    COIN_ID_MAP,
    MarketSnapshot,
    _ticker_to_coin_id,
    fetch_ohlcv_coingecko,
    fetch_recent_market_data,
    synthetic_ohlcv,
)


# --- _ticker_to_coin_id -------------------------------------------------------

def test_ticker_to_coin_id_common_symbols():
    assert _ticker_to_coin_id("BTC") == "bitcoin"
    assert _ticker_to_coin_id("ETH") == "ethereum"
    assert _ticker_to_coin_id("SOL") == "solana"


def test_ticker_to_coin_id_handles_pairs():
    assert _ticker_to_coin_id("BTC/USDT") == "bitcoin"
    assert _ticker_to_coin_id("eth/usd") == "ethereum"


def test_ticker_to_coin_id_lowercases_unknown():
    # 不在 map 里的就当 coin_id 用，小写
    assert _ticker_to_coin_id("RandomCoin") == "randomcoin"


# --- synthetic_ohlcv ---------------------------------------------------------

def test_synthetic_ohlcv_default_shape():
    df = synthetic_ohlcv()
    assert len(df) == 90
    assert "price" in df.columns
    assert "volume" in df.columns


def test_synthetic_ohlcv_custom_length():
    df = synthetic_ohlcv(n_days=30)
    assert len(df) == 30


def test_synthetic_ohlcv_deterministic_with_seed():
    df1 = synthetic_ohlcv(seed=42)
    df2 = synthetic_ohlcv(seed=42)
    assert (df1["price"].values == df2["price"].values).all()


def test_synthetic_ohlcv_positive_prices():
    df = synthetic_ohlcv(start_price=50_000, daily_vol=0.05, n_days=100)
    assert (df["price"] > 0).all()


# --- fetch_recent_market_data (mocked HTTP) ----------------------------------

def test_fetch_recent_market_data_parses_response():
    fake_resp = {
        "bitcoin": {
            "usd": 50000.0,
            "usd_24h_change": 2.5,
            "usd_24h_vol": 25_000_000_000,
            "usd_market_cap": 1_000_000_000_000,
        }
    }
    with patch("scripts.data_fetch._http_get_json", return_value=fake_resp):
        snap = fetch_recent_market_data("BTC")
    assert isinstance(snap, MarketSnapshot)
    assert snap.current_price == 50000.0
    assert snap.change_24h_pct == 2.5
    assert snap.coin_id == "bitcoin"
    assert snap.ticker == "BTC"


def test_fetch_recent_market_data_raises_on_empty():
    with patch("scripts.data_fetch._http_get_json", return_value={}):
        with pytest.raises(RuntimeError, match="bitcoin"):
            fetch_recent_market_data("BTC")


def test_market_snapshot_to_dict():
    snap = MarketSnapshot(ticker="BTC", coin_id="bitcoin",
                          current_price=50000, change_24h_pct=1.5,
                          volume_24h=1e10, market_cap=1e12)
    d = snap.to_dict()
    assert d["ticker"] == "BTC"
    assert d["current_price"] == 50000.0


# --- fetch_ohlcv_coingecko (mocked) -----------------------------------------

def test_fetch_ohlcv_coingecko_parses_prices():
    fake = {
        "prices": [[1700000000000, 40000], [1700086400000, 41000], [1700172800000, 42000]],
        "total_volumes": [[1700000000000, 1e9], [1700086400000, 1.5e9], [1700172800000, 1.2e9]],
    }
    with patch("scripts.data_fetch._http_get_json", return_value=fake):
        df = fetch_ohlcv_coingecko("BTC", days=3)
    assert len(df) == 3
    assert list(df["price"]) == [40000, 41000, 42000]


def test_fetch_ohlcv_coingecko_raises_on_empty():
    with patch("scripts.data_fetch._http_get_json", return_value={}):
        with pytest.raises(RuntimeError):
            fetch_ohlcv_coingecko("BTC")


# --- 注册表 -------------------------------------------------------------------

def test_coin_id_map_has_common_coins():
    for ticker in ["BTC", "ETH", "SOL", "BNB"]:
        assert ticker in COIN_ID_MAP
