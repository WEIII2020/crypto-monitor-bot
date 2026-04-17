from abc import ABC, abstractmethod
from typing import List, Dict
import asyncio

from src.utils.logger import logger


class BaseCollector(ABC):
    """Abstract base class for exchange data collectors"""

    def __init__(self, exchange: str):
        self.exchange = exchange
        self.connected = False
        self.subscribed_symbols: List[str] = []
        self.retry_delays = [1, 2, 5, 10, 30, 60]  # Exponential backoff
        self.max_retries = 10

    @abstractmethod
    async def connect(self):
        """Establish connection to exchange"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection to exchange"""
        pass

    @abstractmethod
    async def subscribe_symbols(self, symbols: List[str]):
        """Subscribe to price updates for symbols"""
        pass

    async def connect_with_retry(self):
        """Connect with exponential backoff retry logic"""
        for attempt in range(self.max_retries):
            try:
                await self.connect()
                self.connected = True
                logger.info(f"{self.exchange} connected successfully")
                return True
            except Exception as e:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                logger.warning(
                    f"{self.exchange} connection attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay}s"
                )
                await asyncio.sleep(delay)

        logger.error(f"{self.exchange} connection failed after {self.max_retries} attempts")
        return False

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format (e.g., BTCUSDT -> BTC/USDT)"""
        # Override in subclass if needed
        return symbol

    def normalize_price_data(self, raw_data: Dict) -> Dict:
        """Normalize price data to standard format"""
        return {
            'symbol': raw_data.get('symbol'),
            'price': float(raw_data.get('price', 0)),
            'volume': float(raw_data.get('volume', 0)),
            'timestamp': raw_data.get('timestamp'),
            'exchange': self.exchange
        }
