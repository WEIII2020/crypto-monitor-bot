import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis

from src.config import config
from src.utils.logger import logger


class RedisClient:
    """Async Redis client for caching and state management"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        redis_url = config.redis_url if config else 'redis://localhost:6379/0'
        self.redis = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis connected")

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.aclose()
            logger.info("Redis disconnected")

    async def flush_db(self):
        """Flush current database (for testing)"""
        if self.redis:
            await self.redis.flushdb()

    def _price_key(self, exchange: str, symbol: str) -> str:
        """Generate Redis key for price data"""
        return f"price:{exchange}:{symbol}:1m"

    async def store_price(
        self,
        exchange: str,
        symbol: str,
        timestamp: float,
        price_data: Dict
    ):
        """Store price data in sorted set with timestamp as score"""
        key = self._price_key(exchange, symbol)
        value = json.dumps(price_data)

        # Add to sorted set
        await self.redis.zadd(key, {value: timestamp})

        # Set TTL to 2 hours
        await self.redis.expire(key, 7200)

    async def get_prices(
        self,
        exchange: str,
        symbol: str,
        minutes: int
    ) -> List[Dict]:
        """Get prices within last N minutes"""
        key = self._price_key(exchange, symbol)
        cutoff = datetime.now().timestamp() - (minutes * 60)

        # Get all prices after cutoff, sorted by timestamp ascending
        prices = await self.redis.zrangebyscore(
            key, cutoff, '+inf', withscores=True
        )

        result = []
        for price_json, timestamp in reversed(prices):
            data = json.loads(price_json)
            data['timestamp'] = timestamp
            result.append(data)

        return result

    async def get_avg_volume(
        self,
        exchange: str,
        symbol: str,
        minutes: int
    ) -> float:
        """Calculate average volume over last N minutes"""
        prices = await self.get_prices(exchange, symbol, minutes)

        if not prices:
            return 0.0

        total_volume = sum(p.get('volume', 0) for p in prices)
        return total_volume / len(prices)

    async def check_alert_sent(self, symbol: str, alert_type: str) -> bool:
        """Check if alert was recently sent (for deduplication)"""
        key = f"alert:sent:{symbol}:{alert_type}"
        exists = await self.redis.exists(key)
        return bool(exists)

    async def mark_alert_sent(
        self,
        symbol: str,
        alert_type: str,
        ttl_seconds: int = 300
    ):
        """Mark alert as sent with TTL (default 5 minutes)"""
        key = f"alert:sent:{symbol}:{alert_type}"
        await self.redis.setex(key, ttl_seconds, "1")

    async def set_ws_status(self, exchange: str, status: str):
        """Update WebSocket connection status"""
        key = f"ws:status:{exchange}"
        await self.redis.set(key, status)

    async def get_ws_status(self, exchange: str) -> str:
        """Get WebSocket connection status"""
        key = f"ws:status:{exchange}"
        status = await self.redis.get(key)
        return status or "disconnected"

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set value with optional expiration (seconds)"""
        if ex:
            await self.redis.setex(key, ex, value)
        else:
            await self.redis.set(key, value)


# Global client instance
redis_client = RedisClient()
