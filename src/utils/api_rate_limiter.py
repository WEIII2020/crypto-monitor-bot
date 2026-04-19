"""
API Rate Limiter - API 限流工具

功能：
- 指数退避重试
- 请求速率控制
- 统一的错误处理
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from src.utils.logger import logger


class APIRateLimiter:
    """
    API 限流器

    特点：
    - 自动指数退避
    - 统计限流次数
    - 智能延迟调整
    """

    def __init__(self, max_concurrent: int = 10, base_delay: float = 0.1):
        """
        Args:
            max_concurrent: 最大并发请求数
            base_delay: 基础延迟（秒）
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.base_delay = base_delay
        self.current_delay = base_delay

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'rate_limited': 0,
            'errors': 0,
            'last_rate_limit': None
        }

    async def fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: int = 5
    ) -> Optional[Dict]:
        """
        带重试的 API 请求

        Args:
            session: aiohttp session
            url: API URL
            params: 请求参数
            max_retries: 最大重试次数
            timeout: 超时时间（秒）

        Returns:
            API 响应数据或 None
        """
        async with self.semaphore:
            self.stats['total_requests'] += 1

            for attempt in range(max_retries):
                try:
                    async with session.get(url, params=params, timeout=timeout) as resp:
                        if resp.status == 200:
                            # 成功：逐渐降低延迟
                            self.current_delay = max(self.base_delay, self.current_delay * 0.9)
                            await asyncio.sleep(self.current_delay)
                            return await resp.json()

                        elif resp.status == 418:  # Binance 限流
                            self.stats['rate_limited'] += 1
                            self.stats['last_rate_limit'] = datetime.now()

                            # 指数退避
                            wait_time = self.base_delay * (2 ** attempt)
                            self.current_delay = min(5.0, wait_time)  # 最多 5 秒

                            logger.warning(
                                f"⚠️ API 限流 (418) - 等待 {wait_time:.1f}s 后重试 "
                                f"(尝试 {attempt + 1}/{max_retries})"
                            )

                            await asyncio.sleep(wait_time)
                            continue

                        elif resp.status == 429:  # 通用限流
                            self.stats['rate_limited'] += 1
                            wait_time = self.base_delay * (2 ** attempt)

                            logger.warning(f"⚠️ API 限流 (429) - 等待 {wait_time:.1f}s")
                            await asyncio.sleep(wait_time)
                            continue

                        else:
                            # 其他错误
                            self.stats['errors'] += 1
                            logger.debug(f"API 错误: {resp.status} - {url}")
                            return None

                except asyncio.TimeoutError:
                    self.stats['errors'] += 1
                    logger.debug(f"API 超时: {url}")
                    if attempt == max_retries - 1:
                        return None
                    await asyncio.sleep(self.base_delay * (attempt + 1))

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.debug(f"API 异常: {e}")
                    if attempt == max_retries - 1:
                        return None
                    await asyncio.sleep(self.base_delay * (attempt + 1))

            return None

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()

        # 计算成功率
        total = stats['total_requests']
        if total > 0:
            stats['success_rate'] = (total - stats['errors']) / total * 100
            stats['rate_limit_pct'] = stats['rate_limited'] / total * 100
        else:
            stats['success_rate'] = 0
            stats['rate_limit_pct'] = 0

        stats['current_delay'] = self.current_delay

        return stats

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'rate_limited': 0,
            'errors': 0,
            'last_rate_limit': None
        }
