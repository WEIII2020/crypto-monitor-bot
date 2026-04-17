from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert
from tenacity import retry, stop_after_attempt, wait_exponential

from src.database.models import Base, Symbol, PriceData, Alert, MarketMakerAnalysis
from src.config import config
from src.utils.logger import logger


class PostgresClient:
    """Async PostgreSQL client for database operations"""

    def __init__(self, database_url: Optional[str] = None):
        # Use provided URL or get from config
        if database_url:
            db_url = database_url
        elif config:
            db_url = config.database_url
        else:
            raise ValueError("database_url must be provided or config must be initialized")
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
        elif db_url.startswith('sqlite://'):
            db_url = db_url.replace('sqlite://', 'sqlite+aiosqlite://')

        # Configure connection pool for high concurrency
        self.engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=20,           # Number of persistent connections
            max_overflow=10,        # Additional connections when pool is full
            pool_pre_ping=True,     # Verify connections before using
            pool_recycle=3600,      # Recycle connections after 1 hour
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.session: Optional[AsyncSession] = None

    async def connect(self):
        """Initialize database connection and create tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL connected and tables created")

    async def disconnect(self):
        """Close database connection"""
        await self.engine.dispose()
        logger.info("PostgreSQL disconnected")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def insert_symbol(self, symbol_data: Dict) -> int:
        """Insert a new symbol or return existing ID"""
        async with self.async_session() as session:
            # Check if symbol already exists
            stmt = select(Symbol).where(
                Symbol.symbol == symbol_data['symbol'],
                Symbol.exchange == symbol_data['exchange']
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                return existing.id

            # Insert new symbol
            new_symbol = Symbol(**symbol_data)
            session.add(new_symbol)
            await session.commit()
            await session.refresh(new_symbol)

            logger.debug(f"Inserted symbol: {symbol_data['symbol']} on {symbol_data['exchange']}")
            return new_symbol.id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_symbol(self, symbol: str, exchange: str) -> Optional[Dict]:
        """Get symbol by name and exchange"""
        async with self.async_session() as session:
            stmt = select(Symbol).where(
                Symbol.symbol == symbol,
                Symbol.exchange == exchange
            )
            result = await session.execute(stmt)
            symbol_obj = result.scalar_one_or_none()

            if not symbol_obj:
                return None

            return {
                'id': symbol_obj.id,
                'symbol': symbol_obj.symbol,
                'exchange': symbol_obj.exchange,
                'base_currency': symbol_obj.base_currency,
                'quote_currency': symbol_obj.quote_currency,
                'is_active': symbol_obj.is_active
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def insert_price_data(self, price_data: Dict) -> int:
        """Insert price data record"""
        async with self.async_session() as session:
            new_price = PriceData(**price_data)
            session.add(new_price)
            await session.commit()
            await session.refresh(new_price)
            return new_price.id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def insert_alert(self, alert_data: Dict) -> int:
        """Insert alert record"""
        async with self.async_session() as session:
            new_alert = Alert(**alert_data)
            session.add(new_alert)
            await session.commit()
            await session.refresh(new_alert)
            return new_alert.id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_recent_prices(
        self,
        symbol_id: int,
        exchange: str,
        minutes: int
    ) -> List[Dict]:
        """Get recent price data for symbol"""
        async with self.async_session() as session:
            from sqlalchemy import and_
            from datetime import timedelta

            cutoff = datetime.now() - timedelta(minutes=minutes)

            stmt = select(PriceData).where(
                and_(
                    PriceData.symbol_id == symbol_id,
                    PriceData.exchange == exchange,
                    PriceData.timestamp >= cutoff
                )
            ).order_by(PriceData.timestamp.desc())

            result = await session.execute(stmt)
            prices = result.scalars().all()

            return [
                {
                    'timestamp': p.timestamp,
                    'open': float(p.open),
                    'high': float(p.high),
                    'low': float(p.low),
                    'close': float(p.close),
                    'volume': float(p.volume)
                }
                for p in prices
            ]


# Global client instance (initialized when config is available)
postgres_client = None

# Initialize client if config is available
if config:
    postgres_client = PostgresClient()
