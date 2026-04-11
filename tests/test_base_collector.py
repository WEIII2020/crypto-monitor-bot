import pytest
from src.collectors.base_collector import BaseCollector


class MockCollector(BaseCollector):
    """Mock collector for testing"""

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def subscribe_symbols(self, symbols):
        self.subscribed_symbols = symbols


@pytest.mark.asyncio
async def test_base_collector_initialization():
    """Test base collector initialization"""
    collector = MockCollector('test_exchange')

    assert collector.exchange == 'test_exchange'
    assert collector.connected is False


@pytest.mark.asyncio
async def test_base_collector_connect_disconnect():
    """Test collector connection lifecycle"""
    collector = MockCollector('test_exchange')

    await collector.connect()
    assert collector.connected is True

    await collector.disconnect()
    assert collector.connected is False


@pytest.mark.asyncio
async def test_base_collector_subscribe():
    """Test symbol subscription"""
    collector = MockCollector('test_exchange')
    symbols = ['BTC/USDT', 'ETH/USDT']

    await collector.subscribe_symbols(symbols)

    assert collector.subscribed_symbols == symbols
