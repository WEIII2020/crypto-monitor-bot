import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
import fakeredis.aioredis
from src.database.redis_client import RedisClient


@pytest_asyncio.fixture
async def redis_client():
    """Fixture providing Redis client with fakeredis"""
    client = RedisClient()
    # Use fakeredis for testing
    client.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await client.flush_db()  # Clean test database
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_store_price(redis_client):
    """Test storing price in Redis sorted set"""
    timestamp = datetime.now().timestamp()
    price_data = {'price': 50000.0, 'volume': 100.5}

    await redis_client.store_price('binance', 'BTC/USDT', timestamp, price_data)

    prices = await redis_client.get_prices('binance', 'BTC/USDT', minutes=5)
    assert len(prices) == 1
    assert prices[0]['price'] == 50000.0


@pytest.mark.asyncio
async def test_get_prices_window(redis_client):
    """Test retrieving prices within time window"""
    now = datetime.now().timestamp()

    # Store 3 prices 1 minute apart
    for i in range(3):
        timestamp = now - (i * 60)
        await redis_client.store_price(
            'binance', 'BTC/USDT', timestamp,
            {'price': 50000.0 + i * 100, 'volume': 100.0}
        )

    # Get last 5 minutes
    prices = await redis_client.get_prices('binance', 'BTC/USDT', minutes=5)

    assert len(prices) == 3
    # Sorted by timestamp descending (newest first)
    assert prices[0]['timestamp'] > prices[1]['timestamp']
    assert prices[1]['timestamp'] > prices[2]['timestamp']


@pytest.mark.asyncio
async def test_check_alert_sent(redis_client):
    """Test alert deduplication"""
    # First check should return False (not sent)
    sent = await redis_client.check_alert_sent('BTC/USDT', 'PRICE_SPIKE')
    assert sent is False

    # Mark as sent
    await redis_client.mark_alert_sent('BTC/USDT', 'PRICE_SPIKE', ttl_seconds=300)

    # Second check should return True (already sent)
    sent = await redis_client.check_alert_sent('BTC/USDT', 'PRICE_SPIKE')
    assert sent is True


@pytest.mark.asyncio
async def test_get_avg_volume(redis_client):
    """Test calculating average volume"""
    now = datetime.now().timestamp()

    # Store 3 volume data points
    volumes = [100.0, 200.0, 300.0]
    for i, vol in enumerate(volumes):
        timestamp = now - (i * 60)
        await redis_client.store_price(
            'binance', 'BTC/USDT', timestamp,
            {'price': 50000.0, 'volume': vol}
        )

    avg = await redis_client.get_avg_volume('binance', 'BTC/USDT', minutes=5)

    assert avg == 200.0  # (100 + 200 + 300) / 3
