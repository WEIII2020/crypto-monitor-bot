"""
Binance Square Monitor - 币安广场热度监控
基于 lana 的方法：广场是散户信息聚集的地方，人气是散户进场的早期信号
"""

import aiohttp
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.database.redis_client import redis_client
from src.utils.logger import logger


class SquareMonitor:
    """
    币安广场热度监控器

    核心逻辑（lana方法）：
    - 每天帖子量最高的币种
    - 每天讨论量最高的币种
    - 庄家拉盘之前必须先有鱼，广场人气是散户进场的早期信号
    """

    def __init__(self):
        # TODO: 币安广场API（需要实际的API endpoint）
        # 目前使用占位符，实际部署时需要配置
        self.square_api = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"

        # lana的阈值
        self.min_mentions = 100          # 最小提及次数
        self.trending_threshold = 50     # 热度阈值
        self.alert_cooldown_seconds = 7200  # 2小时冷却

        # 缓存
        self.mention_cache: Dict[str, int] = {}
        self.last_update: Optional[datetime] = None

    async def check_trending(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        检测币种在广场的热度

        Returns:
            alert dict if trending, None otherwise
        """
        try:
            # 1. 获取广场热度（从缓存或API）
            if not self.mention_cache or self._should_refresh_cache():
                await self._refresh_trending_coins()

            # 2. 检查该币种的提及次数
            mentions = self.mention_cache.get(symbol, 0)

            if mentions < self.min_mentions:
                return None

            # 3. 检查是否达到热度阈值
            # 计算相对热度（与平均值对比）
            avg_mentions = sum(self.mention_cache.values()) / len(self.mention_cache) if self.mention_cache else 0

            if avg_mentions == 0:
                return None

            heat_score = (mentions / avg_mentions) * 100

            if heat_score < self.trending_threshold:
                return None

            # 4. 检测到热度信号！
            logger.info(
                f"🔥 广场热度: {symbol} | "
                f"提及{mentions}次 | "
                f"热度{heat_score:.0f}"
            )

            # 5. 去重检查
            alert_key = f"SQUARE_TRENDING_{symbol}"
            already_sent = await redis_client.check_alert_sent(symbol, alert_key)

            if already_sent:
                return None

            # 标记已发送（2小时冷却）
            await redis_client.mark_alert_sent(
                symbol,
                alert_key,
                ttl_seconds=self.alert_cooldown_seconds
            )

            # 6. 返回信号
            return {
                'symbol': symbol,
                'exchange': exchange,
                'alert_type': 'SQUARE_TRENDING',
                'alert_level': 'INFO',
                'mentions': mentions,
                'heat_score': round(heat_score, 1),
                'score': 20,  # 信号评分（用于融合）
                'message': self._format_message(
                    symbol,
                    mentions,
                    heat_score
                )
            }

        except Exception as e:
            logger.error(f"Error checking square trending for {symbol}: {e}")
            return None

    async def _refresh_trending_coins(self):
        """
        刷新热门币种缓存

        TODO: 实际部署时需要：
        1. 使用 Binance Square API
        2. 或使用你已安装的 Binance Square Skill
        3. 抓取最近24小时的帖子
        4. 统计币种提及频率
        """
        try:
            logger.info("正在刷新广场热度...")

            # 方法1：使用Binance Square API（如果有）
            # trending_data = await self._fetch_from_api()

            # 方法2：使用Binance Square Skill（推荐）
            # trending_data = await self._fetch_from_skill()

            # 方法3：模拟数据（测试用）
            trending_data = await self._fetch_mock_data()

            # 更新缓存
            self.mention_cache = trending_data
            self.last_update = datetime.now()

            logger.info(f"✅ 广场热度已更新: {len(trending_data)} 个币种")

        except Exception as e:
            logger.error(f"Error refreshing trending coins: {e}")

    async def _fetch_from_api(self) -> Dict[str, int]:
        """
        从币安广场API获取数据

        TODO: 实现实际的API调用
        """
        try:
            # 这里需要实际的API调用逻辑
            # 币安广场可能需要登录或特定的token

            async with aiohttp.ClientSession() as session:
                # 示例：获取热门文章
                params = {
                    'type': 1,  # 文章类型
                    'pageNo': 1,
                    'pageSize': 100
                }

                async with session.post(
                    self.square_api,
                    json=params,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Square API error: {response.status}")
                        return {}

                    data = await response.json()

                    # 解析文章内容，提取币种提及
                    mentions = self._parse_mentions(data)

                    return mentions

        except Exception as e:
            logger.error(f"Error fetching from API: {e}")
            return {}

    async def _fetch_from_skill(self) -> Dict[str, int]:
        """
        使用Binance Square Skill获取数据

        TODO: 集成你已安装的Skill
        需要调用 skill 的方法来获取广场数据
        """
        try:
            # 这里需要调用你的Binance Square Skill
            # 例如：
            # from skills.binance_square import BinanceSquareSkill
            # skill = BinanceSquareSkill()
            # posts = await skill.get_trending_posts(hours=24)
            # mentions = self._parse_mentions(posts)
            # return mentions

            logger.warning("Binance Square Skill 集成待实现")
            return {}

        except Exception as e:
            logger.error(f"Error fetching from skill: {e}")
            return {}

    async def _fetch_mock_data(self) -> Dict[str, int]:
        """
        模拟数据（用于测试）

        实际部署时替换为真实数据源
        """
        # 模拟一些热门币种的提及次数
        mock_data = {
            'BTC/USDT': 500,
            'ETH/USDT': 350,
            'SOL/USDT': 280,
            'BNB/USDT': 200,
            'DOGE/USDT': 150,
            'SHIB/USDT': 120,
            'AVAX/USDT': 95,
            'LINK/USDT': 80,
        }

        logger.debug(f"使用模拟数据: {len(mock_data)} 个币种")
        return mock_data

    def _parse_mentions(self, data: Dict) -> Dict[str, int]:
        """
        解析数据，统计币种提及次数

        Args:
            data: API返回的数据

        Returns:
            {symbol: mention_count}
        """
        mentions = defaultdict(int)

        try:
            # TODO: 根据实际API结构解析
            # 这里需要根据币安广场的实际数据结构来实现

            # 示例逻辑：
            # for article in data.get('articles', []):
            #     content = article.get('content', '')
            #     for symbol in self._extract_symbols(content):
            #         mentions[symbol] += 1

            pass

        except Exception as e:
            logger.error(f"Error parsing mentions: {e}")

        return dict(mentions)

    def _should_refresh_cache(self) -> bool:
        """判断是否需要刷新缓存（每小时刷新一次）"""
        if not self.last_update:
            return True

        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed > 3600  # 1小时

    def _format_message(
        self,
        symbol: str,
        mentions: int,
        heat_score: float
    ) -> str:
        """
        格式化告警消息
        """
        lines = [
            f"🔥 广场热度 - 散户关注度高",
            f"",
            f"🪙 {symbol}",
            f"📊 24小时统计:",
            f"  • 提及次数: {mentions}次",
            f"  • 热度指数: {heat_score:.0f}",
            f"",
            f"🎯 lana方法:",
            f"  • 广场是散户聚集地",
            f"  • 庄家拉盘前必须先有鱼",
            f"  • 人气是散户进场的早期信号",
            f"",
            f"⚠️  注意:",
            f"  • 结合其他信号判断",
            f"  • 高热度不等于上涨",
            f"  • 可能是庄家造势",
        ]

        return '\n'.join(lines)

    def get_trending_symbols(self, top_n: int = 10) -> List[str]:
        """
        获取当前最热门的币种

        Args:
            top_n: 返回前N个

        Returns:
            List of symbols sorted by mentions
        """
        sorted_symbols = sorted(
            self.mention_cache.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [symbol for symbol, _ in sorted_symbols[:top_n]]


# 备注：实际部署时的集成步骤
"""
TODO: 实际部署时需要完成：

1. 获取币安广场API访问权限
   - 或使用网页爬虫（需要遵守条款）
   - 或使用第三方数据服务

2. 集成你已安装的 Binance Square Skill
   - 在 hermes-agent-bot 中调用
   - 获取帖子数据并分析

3. 实现币种识别算法
   - 从文章内容中提取币种符号
   - 处理各种格式（BTC、Bitcoin、$BTC等）

4. 优化统计逻辑
   - 区分普通提及和深度讨论
   - 考虑帖子的点赞数、评论数作为权重
   - 过滤垃圾内容和重复帖子

5. 定期更新
   - 每小时刷新一次热度数据
   - 缓存到Redis避免频繁请求
"""
