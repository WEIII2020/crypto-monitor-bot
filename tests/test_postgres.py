import pytest
import pytest_asyncio
from datetime import datetime
from src.database.postgres import PostgresClient
from src.database.models import Symbol


@pytest_asyncio.fixture
async def pg_client():
    """Fixture providing PostgreSQL client with test database"""
    client = PostgresClient(database_url='sqlite:///:memory:')
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_insert_symbol(pg_client):
    """Test inserting a symbol into database"""
    symbol_data = {
        'symbol': 'BTC/USDT',
        'exchange': 'binance',
        'base_currency': 'BTC',
        'quote_currency': 'USDT'
    }

    symbol_id = await pg_client.insert_symbol(symbol_data)

    assert symbol_id is not None
    assert isinstance(symbol_id, int)


@pytest.mark.asyncio
async def test_get_symbol_by_name(pg_client):
    """Test retrieving symbol by name and exchange"""
    await pg_client.insert_symbol({
        'symbol': 'ETH/USDT',
        'exchange': 'okx',
        'base_currency': 'ETH',
        'quote_currency': 'USDT'
    })

    symbol = await pg_client.get_symbol('ETH/USDT', 'okx')

    assert symbol is not None
    assert symbol['symbol'] == 'ETH/USDT'
    assert symbol['exchange'] == 'okx'


@pytest.mark.asyncio
async def test_insert_price_data(pg_client):
    """Test inserting price data"""
    symbol_id = await pg_client.insert_symbol({
        'symbol': 'BTC/USDT',
        'exchange': 'binance',
        'base_currency': 'BTC',
        'quote_currency': 'USDT'
    })

    price_data = {
        'symbol_id': symbol_id,
        'exchange': 'binance',
        'timestamp': datetime.now(),
        'open': 50000.0,
        'high': 51000.0,
        'low': 49500.0,
        'close': 50500.0,
        'volume': 100.5,
        'quote_volume': 5050000.0
    }

    result = await pg_client.insert_price_data(price_data)

    assert result is not None
