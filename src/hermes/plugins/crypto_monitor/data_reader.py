"""
Reads alert data from the crypto-monitor-bot's PostgreSQL/Redis databases.
DB URLs are read from the same env vars used by crypto-monitor-bot.
"""

import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

import logging
logger = logging.getLogger(__name__)


@dataclass
class Alert:
    id: int
    symbol: str
    alert_type: str
    alert_level: str
    score: Optional[int]
    price: float
    change_percent: float
    message: str
    created_at: datetime


class MonitorDataReader:
    """Reads monitoring data from the shared PostgreSQL/Redis instance."""

    def __init__(self):
        self.postgres_url = os.getenv(
            "DATABASE_URL",
            "postgresql://cryptobot:P%40ssw0rd2024%21Crypto%23DB@localhost:5432/crypto_monitor",
        )
        self.redis_url = os.getenv(
            "REDIS_URL",
            "redis://:R3dis%24Secure%232024Pass%21@localhost:6379/0",
        )
        self.pg_pool = None
        self.redis_client = None

    async def connect(self) -> bool:
        try:
            import asyncpg
            self.pg_pool = await asyncpg.create_pool(self.postgres_url, min_size=1, max_size=5)
        except Exception as e:
            logger.warning("MonitorDataReader: PostgreSQL connect failed: %s", e)
            return False

        try:
            import redis.asyncio as aioredis
            self.redis_client = await aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        except Exception as e:
            logger.warning("MonitorDataReader: Redis connect failed: %s", e)

        return True

    async def disconnect(self):
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis_client:
            await self.redis_client.aclose()

    async def get_recent_alerts(
        self, minutes: int = 60, alert_types: Optional[List[str]] = None
    ) -> List[Alert]:
        if not self.pg_pool:
            return []
        since = datetime.now() - timedelta(minutes=minutes)
        query = """
            SELECT a.id, s.symbol, a.alert_type, a.alert_level,
                   a.price, a.change_percent, a.message, a.created_at
            FROM alerts a
            JOIN symbols s ON a.symbol_id = s.id
            WHERE a.created_at > $1
        """
        params: list = [since]
        if alert_types:
            query += " AND a.alert_type = ANY($2)"
            params.append(alert_types)
        query += " ORDER BY a.created_at DESC"

        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
        except Exception as e:
            logger.error("get_recent_alerts error: %s", e)
            return []

        alerts = []
        for row in rows:
            score = None
            if "FUSION" in row["alert_type"]:
                score = self._extract_score(row["message"])
            alerts.append(Alert(
                id=row["id"],
                symbol=row["symbol"],
                alert_type=row["alert_type"],
                alert_level=row["alert_level"],
                score=score,
                price=float(row["price"] or 0),
                change_percent=float(row["change_percent"] or 0),
                message=row["message"],
                created_at=row["created_at"],
            ))
        return alerts

    async def get_fusion_signals(self, minutes: int = 10, min_score: int = 85) -> List[Alert]:
        alerts = await self.get_recent_alerts(minutes=minutes, alert_types=["SIGNAL_FUSION"])
        return [a for a in alerts if a.score and a.score >= min_score]

    async def get_alert_stats(self, hours: int = 24) -> Dict:
        if not self.pg_pool:
            return {"total": 0, "by_type": {}, "by_level": {}}
        since = datetime.now() - timedelta(hours=hours)
        query = """
            SELECT alert_type, alert_level, COUNT(*) AS count
            FROM alerts
            WHERE created_at > $1
            GROUP BY alert_type, alert_level
            ORDER BY count DESC
        """
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(query, since)
        except Exception as e:
            logger.error("get_alert_stats error: %s", e)
            return {"total": 0, "by_type": {}, "by_level": {}}

        stats: Dict = {"total": 0, "by_type": {}, "by_level": {}}
        for row in rows:
            t, lv, cnt = row["alert_type"], row["alert_level"], row["count"]
            stats["total"] += cnt
            stats["by_type"][t] = stats["by_type"].get(t, 0) + cnt
            stats["by_level"][lv] = stats["by_level"].get(lv, 0) + cnt
        return stats

    async def get_monitor_status(self) -> Dict:
        status = {
            "postgres_connected": False,
            "redis_connected": False,
            "symbols_count": 0,
            "recent_alerts": 0,
        }
        if self.pg_pool:
            try:
                async with self.pg_pool.acquire() as conn:
                    status["symbols_count"] = await conn.fetchval(
                        "SELECT COUNT(*) FROM symbols WHERE is_active = true"
                    )
                    status["postgres_connected"] = True
            except Exception:
                pass
        if self.redis_client:
            try:
                await self.redis_client.ping()
                status["redis_connected"] = True
            except Exception:
                pass
        status["recent_alerts"] = len(await self.get_recent_alerts(minutes=60))
        return status

    def _extract_score(self, message: str) -> Optional[int]:
        try:
            m = re.search(r"(\d+)/100", message)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return None
