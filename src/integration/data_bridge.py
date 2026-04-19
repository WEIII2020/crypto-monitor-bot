"""
Data Bridge - 数据桥接

提供统一的数据访问接口，让 Hermes Agent 可以读取 crypto-monitor-bot 的数据
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import redis.asyncio as aioredis
from pathlib import Path
import psutil
import os

from src.utils.logger import logger


class DataBridge:
    """数据桥接器"""

    def __init__(self, redis_client=None, postgres_client=None):
        """
        初始化数据桥接器

        Args:
            redis_client: Redis 客户端
            postgres_client: PostgreSQL 客户端
        """
        self.redis = redis_client
        self.postgres = postgres_client
        self.start_time = datetime.now()

        # 信号缓存（从日志文件读取）
        self._signal_cache: List[Dict] = []
        self._last_cache_update = datetime.now()

    async def _ensure_redis(self):
        """确保 Redis 连接"""
        if self.redis is None:
            try:
                self.redis = await aioredis.from_url('redis://localhost:6379', decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
        return self.redis is not None

    async def _read_signals_from_log(self) -> List[Dict]:
        """从日志文件读取信号"""
        try:
            log_file = Path(__file__).parent.parent.parent / "logs" / "bot.log"
            if not log_file.exists():
                return []

            signals = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "NEW SIGNAL" in line or "Signal generated" in line:
                        try:
                            # 解析日志行
                            parts = line.split('|')
                            if len(parts) >= 3:
                                timestamp_str = parts[0].strip()
                                message = parts[-1].strip()

                                signal = {
                                    'timestamp': timestamp_str,
                                    'message': message,
                                    'parsed_at': datetime.now().isoformat()
                                }
                                signals.append(signal)
                        except Exception as e:
                            continue

            return signals[-100:]  # 保留最近 100 条
        except Exception as e:
            logger.error(f"Failed to read signals from log: {e}")
            return []

    async def get_latest_signals(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的交易信号

        Args:
            limit: 返回数量

        Returns:
            信号列表
        """
        try:
            # 每 30 秒更新一次缓存
            if (datetime.now() - self._last_cache_update).total_seconds() > 30:
                self._signal_cache = await self._read_signals_from_log()
                self._last_cache_update = datetime.now()

            return self._signal_cache[-limit:] if self._signal_cache else []
        except Exception as e:
            logger.error(f"Failed to get latest signals: {e}")
            return []

    async def get_signal_by_symbol(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        获取特定币种的信号历史

        Args:
            symbol: 币种符号
            limit: 返回数量

        Returns:
            信号列表
        """
        try:
            all_signals = await self.get_latest_signals(limit=100)
            symbol_signals = [
                s for s in all_signals
                if symbol.upper() in s.get('message', '').upper()
            ]
            return symbol_signals[-limit:]
        except Exception as e:
            logger.error(f"Failed to get signals for {symbol}: {e}")
            return []

    async def get_realtime_price(self, symbol: str) -> Optional[Dict]:
        """
        获取实时价格

        Args:
            symbol: 币种符号

        Returns:
            价格数据
        """
        try:
            if await self._ensure_redis():
                # 尝试从 Redis 读取
                key = f"price:{symbol}"
                data = await self.redis.get(key)
                if data:
                    return json.loads(data)

            # Redis 不可用，返回模拟数据
            return {
                'symbol': symbol,
                'price': 'N/A',
                'source': 'unavailable',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    async def get_system_status(self) -> Dict:
        """
        获取系统状态

        Returns:
            状态信息
        """
        try:
            uptime = datetime.now() - self.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # 获取信号统计
            signals = await self.get_latest_signals(limit=1000)
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            signals_today = len([
                s for s in signals
                if datetime.fromisoformat(s.get('parsed_at', '2000-01-01')) > today_start
            ])

            # 获取进程信息
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent(interval=0.1)

            # 检查监控进程
            monitor_running = any(
                'main_phase2.py' in ' '.join(p.cmdline())
                for p in psutil.process_iter(['pid', 'cmdline'])
            )

            return {
                'status': 'healthy' if monitor_running else 'monitor_offline',
                'uptime': f'{days}d {hours}h {minutes}m',
                'signals_today': signals_today,
                'total_signals_cached': len(signals),
                'monitored_symbols': 200,  # From config
                'memory_mb': round(memory_mb, 1),
                'cpu_percent': round(cpu_percent, 1),
                'monitor_running': monitor_running,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_strategy_status(self) -> Dict:
        """获取策略状态"""
        return {
            'v4a': {'enabled': True, 'signals_today': 0},
            'v7': {'enabled': True, 'signals_today': 0},
            'v8': {'enabled': True, 'signals_today': 0},
            'long': {'enabled': True, 'signals_today': 0}
        }

    async def close(self):
        """关闭连接"""
        if self.redis:
            await self.redis.close()
