from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DECIMAL, TIMESTAMP,
    ForeignKey, Index, BigInteger, Text, JSON
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Symbol(Base):
    """Cryptocurrency symbol/pair information"""
    __tablename__ = 'symbols'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), nullable=False)
    base_currency = Column(String(10))
    quote_currency = Column(String(10))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        Index('idx_symbols_active', 'is_active'),
        Index('uq_symbol_exchange', 'symbol', 'exchange', unique=True),
    )


class PriceData(Base):
    """Historical price and volume data (OHLCV)"""
    __tablename__ = 'price_data'

    id = Column(BigInteger, primary_key=True)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    exchange = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    open = Column(DECIMAL(20, 8))
    high = Column(DECIMAL(20, 8))
    low = Column(DECIMAL(20, 8))
    close = Column(DECIMAL(20, 8))
    volume = Column(DECIMAL(20, 8))
    quote_volume = Column(DECIMAL(20, 8))
    timeframe = Column(String(5), default='1m')

    __table_args__ = (
        Index('idx_price_symbol_time', 'symbol_id', 'timestamp'),
        Index('idx_price_exchange_time', 'exchange', 'timestamp'),
    )


class Alert(Base):
    """Alert records sent to users"""
    __tablename__ = 'alerts'

    id = Column(BigInteger, primary_key=True)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    exchange = Column(String(20), nullable=False)
    alert_type = Column(String(20), nullable=False)
    alert_level = Column(String(10), nullable=False)
    phase = Column(String(20))
    price = Column(DECIMAL(20, 8))
    change_percent = Column(DECIMAL(10, 2))
    volume_multiplier = Column(DECIMAL(10, 2))
    message = Column(Text)
    sent_at = Column(TIMESTAMP, server_default=func.now())
    confidence = Column(String(10))

    __table_args__ = (
        Index('idx_alerts_time', 'sent_at'),
        Index('idx_alerts_symbol', 'symbol_id', 'sent_at'),
    )


class MarketMakerAnalysis(Base):
    """Market maker phase detection records"""
    __tablename__ = 'market_maker_analysis'

    id = Column(BigInteger, primary_key=True)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    exchange = Column(String(20), nullable=False)
    detected_at = Column(TIMESTAMP, nullable=False)
    phase = Column(String(20), nullable=False)
    phase_start_time = Column(TIMESTAMP)
    confidence = Column(String(10))
    metrics = Column(JSON)
    notes = Column(Text)

    __table_args__ = (
        Index('idx_mm_symbol_time', 'symbol_id', 'detected_at'),
    )


class UserConfig(Base):
    """User configuration and preferences"""
    __tablename__ = 'user_config'

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))

    # Alert thresholds
    warning_threshold_5m = Column(DECIMAL(5, 2), default=10.0)
    critical_threshold_5m = Column(DECIMAL(5, 2), default=20.0)
    volume_warning_multiplier = Column(DECIMAL(5, 2), default=5.0)
    volume_critical_multiplier = Column(DECIMAL(5, 2), default=10.0)

    # Notification preferences
    enable_night_mode = Column(Boolean, default=False)
    night_start_hour = Column(Integer, default=23)
    night_end_hour = Column(Integer, default=7)

    # Subscribed symbols (JSON array)
    subscribed_symbols = Column(JSON, default=list)

    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
