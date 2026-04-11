import pytest
from src.collectors.binance_collector import BinanceCollector


@pytest.mark.asyncio
async def test_binance_collector_initialization():
    """Test Binance collector initialization"""
    collector = BinanceCollector()

    assert collector.exchange == 'binance'
    assert collector.ws_url == 'wss://stream.binance.com:9443/ws'
    assert collector.connected is False


@pytest.mark.asyncio
async def test_binance_normalize_symbol():
    """Test symbol normalization from BTCUSDT to BTC/USDT"""
    collector = BinanceCollector()

    # Test standard symbols
    assert collector.normalize_symbol('BTCUSDT') == 'BTC/USDT'
    assert collector.normalize_symbol('ETHUSDT') == 'ETH/USDT'
    assert collector.normalize_symbol('BNBBTC') == 'BNB/BTC'

    # Test edge cases
    assert collector.normalize_symbol('SOLUSDC') == 'SOL/USDC'


@pytest.mark.asyncio
async def test_binance_subscribe_message():
    """Test subscription message format"""
    collector = BinanceCollector()

    # Test single symbol
    message = collector.get_subscribe_message(['BTC/USDT'])
    assert message == {
        'method': 'SUBSCRIBE',
        'params': ['btcusdt@ticker'],
        'id': 1
    }

    # Test multiple symbols
    message = collector.get_subscribe_message(['BTC/USDT', 'ETH/USDT'])
    assert message == {
        'method': 'SUBSCRIBE',
        'params': ['btcusdt@ticker', 'ethusdt@ticker'],
        'id': 1
    }
