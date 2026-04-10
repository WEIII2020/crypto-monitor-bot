import pytest
from datetime import datetime
from src.database.models import Symbol, PriceData, Alert, MarketMakerAnalysis, UserConfig


def test_symbol_model_creation():
    """Test creating a Symbol model instance"""
    symbol = Symbol(
        symbol='BTC/USDT',
        exchange='binance',
        base_currency='BTC',
        quote_currency='USDT',
        is_active=True
    )

    assert symbol.symbol == 'BTC/USDT'
    assert symbol.exchange == 'binance'
    assert symbol.is_active is True


def test_price_data_model_creation():
    """Test creating a PriceData model instance"""
    price_data = PriceData(
        symbol_id=1,
        exchange='binance',
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49500.0,
        close=50500.0,
        volume=100.5,
        quote_volume=5050000.0
    )

    assert price_data.symbol_id == 1
    assert price_data.close == 50500.0
    assert price_data.volume == 100.5


def test_alert_model_creation():
    """Test creating an Alert model instance"""
    alert = Alert(
        symbol_id=1,
        exchange='binance',
        alert_type='PRICE_SPIKE',
        alert_level='CRITICAL',
        price=50000.0,
        change_percent=23.5,
        message='Critical price alert'
    )

    assert alert.alert_type == 'PRICE_SPIKE'
    assert alert.alert_level == 'CRITICAL'
    assert alert.change_percent == 23.5


def test_market_maker_analysis_model_creation():
    """Test creating a MarketMakerAnalysis model instance"""
    analysis = MarketMakerAnalysis(
        symbol_id=1,
        exchange='binance',
        detected_at=datetime.now(),
        phase='ACCUMULATION',
        confidence='HIGH',
        metrics={'volume_ratio': 5.2}
    )
    assert analysis.phase == 'ACCUMULATION'
    assert analysis.confidence == 'HIGH'


def test_user_config_model_creation():
    """Test creating a UserConfig model instance"""
    user_config = UserConfig(
        telegram_user_id=123456789,
        username='testuser',
        warning_threshold_5m=12.5
    )
    assert user_config.telegram_user_id == 123456789
    assert user_config.warning_threshold_5m == 12.5
