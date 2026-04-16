"""
Performance Monitoring Utility
Track system metrics and health
"""

import time
import asyncio
from typing import Dict
from collections import defaultdict
from datetime import datetime

from src.utils.logger import logger


class PerformanceMonitor:
    """Monitor system performance and health"""

    def __init__(self):
        # Counters
        self.message_count = 0
        self.redis_success = 0
        self.redis_failure = 0
        self.postgres_success = 0
        self.postgres_failure = 0
        self.alert_sent = 0

        # Timing
        self.start_time = time.time()
        self.last_report_time = time.time()

        # Per-symbol stats
        self.symbol_counts = defaultdict(int)

    def record_message(self, symbol: str = None):
        """Record a processed message"""
        self.message_count += 1
        if symbol:
            self.symbol_counts[symbol] += 1

    def record_redis_write(self, success: bool):
        """Record Redis write result"""
        if success:
            self.redis_success += 1
        else:
            self.redis_failure += 1

    def record_postgres_write(self, success: bool):
        """Record PostgreSQL write result"""
        if success:
            self.postgres_success += 1
        else:
            self.postgres_failure += 1

    def record_alert(self):
        """Record alert sent"""
        self.alert_sent += 1

    def get_stats(self) -> Dict:
        """Get current statistics"""
        uptime = time.time() - self.start_time
        elapsed = time.time() - self.last_report_time

        return {
            'uptime_seconds': round(uptime, 1),
            'elapsed_seconds': round(elapsed, 1),
            'messages_total': self.message_count,
            'messages_per_second': round(self.message_count / elapsed, 2) if elapsed > 0 else 0,
            'redis': {
                'success': self.redis_success,
                'failure': self.redis_failure,
                'success_rate': round(self.redis_success / max(1, self.redis_success + self.redis_failure) * 100, 1)
            },
            'postgres': {
                'success': self.postgres_success,
                'failure': self.postgres_failure,
                'success_rate': round(self.postgres_success / max(1, self.postgres_success + self.postgres_failure) * 100, 1)
            },
            'alerts': self.alert_sent,
            'top_symbols': dict(sorted(self.symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        }

    def reset_period(self):
        """Reset period counters"""
        self.last_report_time = time.time()
        self.message_count = 0
        self.redis_success = 0
        self.redis_failure = 0
        self.postgres_success = 0
        self.postgres_failure = 0

    def log_stats(self):
        """Log current statistics"""
        stats = self.get_stats()

        logger.info(
            f"📊 Performance Report: "
            f"Uptime={stats['uptime_seconds']}s, "
            f"Messages={stats['messages_total']} ({stats['messages_per_second']}/s), "
            f"Redis={stats['redis']['success_rate']}%, "
            f"Postgres={stats['postgres']['success_rate']}%, "
            f"Alerts={stats['alerts']}"
        )

        # Warn if success rate is low
        if stats['postgres']['success_rate'] < 80 and self.postgres_success + self.postgres_failure > 10:
            logger.warning(
                f"⚠️ PostgreSQL success rate low: {stats['postgres']['success_rate']}% "
                f"({stats['postgres']['failure']} failures)"
            )


# Global monitor instance
performance_monitor = PerformanceMonitor()


async def periodic_stats_logger(interval: int = 300):
    """
    Periodically log performance statistics

    Args:
        interval: Seconds between reports (default: 5 minutes)
    """
    while True:
        await asyncio.sleep(interval)
        performance_monitor.log_stats()
        performance_monitor.reset_period()
