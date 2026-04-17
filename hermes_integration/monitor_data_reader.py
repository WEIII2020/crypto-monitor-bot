"""
Hermes Agent - Monitor Data Reader
读取 crypto-monitor-bot 的监控数据
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncpg
import redis.asyncio as redis
from dataclasses import dataclass


@dataclass
class Alert:
    """告警数据结构"""
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
    """从crypto-monitor-bot读取数据"""

    def __init__(
        self,
        postgres_url: str = "postgresql://cryptobot:P%40ssw0rd2024%21Crypto%23DB@localhost:5432/crypto_monitor",
        redis_url: str = "redis://:R3dis%24Secure%232024Pass%21@localhost:6379/0"
    ):
        self.postgres_url = postgres_url
        self.redis_url = redis_url
        self.pg_pool = None
        self.redis_client = None

    async def connect(self):
        """连接数据库"""
        # PostgreSQL连接池
        self.pg_pool = await asyncpg.create_pool(
            self.postgres_url,
            min_size=2,
            max_size=10
        )

        # Redis连接
        self.redis_client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        print("✅ 已连接到 crypto-monitor-bot 数据库")

    async def disconnect(self):
        """断开连接"""
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis_client:
            await self.redis_client.close()

    async def get_recent_alerts(
        self,
        minutes: int = 60,
        alert_types: Optional[List[str]] = None
    ) -> List[Alert]:
        """
        获取最近的告警

        Args:
            minutes: 时间范围（分钟）
            alert_types: 告警类型过滤，例如 ['SIGNAL_FUSION', 'OI_SPIKE']

        Returns:
            告警列表
        """
        since = datetime.now() - timedelta(minutes=minutes)

        query = """
        SELECT
            a.id,
            s.symbol,
            a.alert_type,
            a.alert_level,
            a.price,
            a.change_percent,
            a.message,
            a.created_at
        FROM alerts a
        JOIN symbols s ON a.symbol_id = s.id
        WHERE a.created_at > $1
        """

        params = [since]

        if alert_types:
            query += " AND a.alert_type = ANY($2)"
            params.append(alert_types)

        query += " ORDER BY a.created_at DESC"

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        alerts = []
        for row in rows:
            # 尝试从message中提取score（融合信号）
            score = None
            if 'FUSION' in row['alert_type']:
                score = self._extract_score_from_message(row['message'])

            alerts.append(Alert(
                id=row['id'],
                symbol=row['symbol'],
                alert_type=row['alert_type'],
                alert_level=row['alert_level'],
                score=score,
                price=float(row['price']) if row['price'] else 0.0,
                change_percent=float(row['change_percent']) if row['change_percent'] else 0.0,
                message=row['message'],
                created_at=row['created_at']
            ))

        return alerts

    async def get_fusion_signals(
        self,
        minutes: int = 10,
        min_score: int = 85
    ) -> List[Alert]:
        """
        获取高分融合信号（适合自动交易）

        Args:
            minutes: 时间范围
            min_score: 最低分数（默认85分，Lana规则的BUY阈值）

        Returns:
            高分融合信号列表
        """
        all_fusion = await self.get_recent_alerts(
            minutes=minutes,
            alert_types=['SIGNAL_FUSION']
        )

        # 过滤高分信号
        high_score = [a for a in all_fusion if a.score and a.score >= min_score]

        return high_score

    async def get_alert_stats(self, hours: int = 24) -> Dict:
        """
        获取告警统计数据

        Args:
            hours: 统计时间范围（小时）

        Returns:
            统计数据字典
        """
        since = datetime.now() - timedelta(hours=hours)

        query = """
        SELECT
            alert_type,
            alert_level,
            COUNT(*) as count,
            AVG(change_percent) as avg_change
        FROM alerts
        WHERE created_at > $1
        GROUP BY alert_type, alert_level
        ORDER BY count DESC
        """

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, since)

        stats = {
            'total': 0,
            'by_type': {},
            'by_level': {}
        }

        for row in rows:
            alert_type = row['alert_type']
            alert_level = row['alert_level']
            count = row['count']

            stats['total'] += count

            if alert_type not in stats['by_type']:
                stats['by_type'][alert_type] = 0
            stats['by_type'][alert_type] += count

            if alert_level not in stats['by_level']:
                stats['by_level'][alert_level] = 0
            stats['by_level'][alert_level] += count

        return stats

    async def get_monitor_status(self) -> Dict:
        """
        获取监控系统状态

        Returns:
            状态信息字典
        """
        status = {
            'postgres_connected': False,
            'redis_connected': False,
            'symbols_count': 0,
            'recent_alerts': 0
        }

        # 检查PostgreSQL
        try:
            async with self.pg_pool.acquire() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM symbols WHERE is_active = true")
                status['symbols_count'] = result
                status['postgres_connected'] = True
        except:
            pass

        # 检查Redis
        try:
            await self.redis_client.ping()
            status['redis_connected'] = True
        except:
            pass

        # 最近1小时告警数
        recent = await self.get_recent_alerts(minutes=60)
        status['recent_alerts'] = len(recent)

        return status

    def _extract_score_from_message(self, message: str) -> Optional[int]:
        """从融合信号消息中提取分数"""
        try:
            # 消息格式: "📊 综合评分: 90/100"
            if '综合评分' in message or 'score' in message.lower():
                import re
                match = re.search(r'(\d+)/100', message)
                if match:
                    return int(match.group(1))
        except:
            pass
        return None


# 使用示例
async def example_usage():
    """使用示例"""
    reader = MonitorDataReader()

    try:
        # 连接
        await reader.connect()

        # 1. 获取最近10分钟的高分融合信号
        print("\n🎯 高分融合信号 (≥85分):")
        fusion_signals = await reader.get_fusion_signals(minutes=10, min_score=85)
        for signal in fusion_signals:
            print(f"  • {signal.symbol}: {signal.score}分 - {signal.message[:50]}...")

        # 2. 获取最近1小时所有告警
        print("\n📊 最近1小时告警:")
        recent = await reader.get_recent_alerts(minutes=60)
        print(f"  总计: {len(recent)}条")

        # 3. 获取24小时统计
        print("\n📈 24小时统计:")
        stats = await reader.get_alert_stats(hours=24)
        print(f"  总告警: {stats['total']}条")
        print(f"  按类型: {stats['by_type']}")

        # 4. 检查监控状态
        print("\n🔍 监控系统状态:")
        status = await reader.get_monitor_status()
        print(f"  PostgreSQL: {'✅' if status['postgres_connected'] else '❌'}")
        print(f"  Redis: {'✅' if status['redis_connected'] else '❌'}")
        print(f"  监控币种: {status['symbols_count']}个")
        print(f"  最近1h告警: {status['recent_alerts']}条")

    finally:
        await reader.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())
