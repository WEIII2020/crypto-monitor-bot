"""
Manipulation Coin Detector (妖币识别器)
识别历史上频繁出现操纵行为的币种

核心原则：
1. 基于历史数据识别操纵频率
2. 时间衰减加权评分
3. 动态维护妖币监控池
4. 不预测未来，只识别特征
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.utils.logger import logger


class ManipulationCoinDetector:
    """识别和跟踪妖币（高操纵币种）"""

    def __init__(self):
        # 操纵事件定义
        self.pump_threshold = 20.0        # 4小时涨幅 >= 20%
        self.pump_duration = 240          # 4小时（分钟）
        self.dump_ratio = 0.5            # 回撤 >= 50%的涨幅
        self.dump_duration = 1440        # 24小时内回撤

        # 评分权重
        self.time_decay = {
            30: 1.0,      # 1个月内：权重100%
            90: 0.7,      # 3个月内：权重70%
            180: 0.4,     # 6个月内：权重40%
        }

        # 妖币特征阈值
        self.min_manipulation_events = 3   # 至少3次操纵事件
        self.min_avg_volatility = 15.0    # 日均波动率 >15%
        self.min_volume = 1_000_000       # 日成交量 >$1M

        # 加分项
        self.bonus_new_listing = 20       # 新上市 (<3月)
        self.bonus_small_cap = 15         # 小市值 (<$50M)
        self.bonus_low_liquidity = 10     # 低流动性

        # 妖币池
        self.manipulation_coins: Dict[str, Dict] = {}
        self.last_update = None
        self.update_interval = 3600       # 每小时更新一次

    async def update_coin_pool(
        self,
        candidate_symbols: Optional[List[str]] = None
    ) -> List[str]:
        """
        更新妖币监控池

        Args:
            candidate_symbols: 候选币种列表，如果为None则使用当前监控列表

        Returns:
            妖币列表（按评分排序）
        """
        try:
            logger.info("🔍 开始更新妖币池...")

            # 如果没有提供候选列表，使用当前监控的币种
            if candidate_symbols is None:
                candidate_symbols = await self._get_current_symbols()

            # 分析每个币种
            results = []
            for symbol in candidate_symbols:
                score_data = await self._analyze_symbol(symbol)
                if score_data and score_data['score'] >= 40:  # 至少中度操纵
                    results.append((symbol, score_data))

            # 按评分排序
            results.sort(key=lambda x: x[1]['score'], reverse=True)

            # 更新妖币池
            self.manipulation_coins = {
                symbol: data for symbol, data in results
            }

            # 分类统计
            ultra_high = sum(1 for _, d in results if d['score'] >= 80)
            high = sum(1 for _, d in results if 60 <= d['score'] < 80)
            medium = sum(1 for _, d in results if 40 <= d['score'] < 60)

            logger.info(f"✅ 妖币池更新完成:")
            logger.info(f"   🔴 超高操纵: {ultra_high} 个")
            logger.info(f"   🟠 高操纵: {high} 个")
            logger.info(f"   🟡 中度操纵: {medium} 个")
            logger.info(f"   📊 总计: {len(results)} 个")

            # 记录更新时间
            self.last_update = datetime.now()

            return [symbol for symbol, _ in results]

        except Exception as e:
            logger.error(f"Error updating manipulation coin pool: {e}")
            return []

    async def _get_current_symbols(self) -> List[str]:
        """获取当前监控的币种列表"""
        # 这里可以从数据库或配置文件获取
        # 暂时返回空列表，实际使用时会从main.py传入
        return []

    async def _analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        分析单个币种的操纵特征

        Returns:
            {
                'score': 85,
                'level': 'ULTRA_HIGH',
                'manipulation_events': 7,
                'avg_volatility': 18.5,
                'features': {...}
            }
        """
        try:
            # 1. 检测历史操纵事件
            manipulation_events = await self._detect_manipulation_events(symbol)

            if len(manipulation_events) < self.min_manipulation_events:
                return None

            # 2. 计算时间加权评分
            weighted_score = self._calculate_weighted_score(manipulation_events)

            # 3. 计算平均波动率
            avg_volatility = await self._calculate_avg_volatility(symbol)

            if avg_volatility < self.min_avg_volatility:
                return None

            # 4. 检查成交量
            avg_volume = await self._get_avg_volume(symbol)

            if avg_volume < self.min_volume:
                return None

            # 5. 计算加分项
            bonus = await self._calculate_bonus(symbol)

            # 6. 综合评分
            final_score = min(100, weighted_score + bonus)

            # 7. 确定等级
            level = self._get_manipulation_level(final_score)

            return {
                'score': final_score,
                'level': level,
                'manipulation_events': len(manipulation_events),
                'avg_volatility': avg_volatility,
                'avg_volume': avg_volume,
                'recent_events': manipulation_events[:3],  # 最近3次
                'features': {
                    'base_score': weighted_score,
                    'bonus': bonus,
                    'last_manipulation': (
                        manipulation_events[0]['timestamp']
                        if manipulation_events else None
                    )
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing symbol {symbol}: {e}")
            return None

    async def _detect_manipulation_events(
        self,
        symbol: str,
        days: int = 180
    ) -> List[Dict]:
        """
        检测历史操纵事件

        操纵事件定义:
        1. 4小时内涨幅 >= 20%
        2. 成交量 > 5x 平均值
        3. 随后24小时内回撤 >= 50%的涨幅
        """
        try:
            events = []

            # 获取历史K线数据（4小时级别）
            # 注意：这里需要实现历史数据查询
            # 为了演示，我们使用简化的逻辑

            # 从PostgreSQL查询历史数据
            if not postgres_client:
                return events

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 查询4小时K线
            # 实际实现需要聚合1小时数据或直接存储4小时数据
            # 这里提供接口定义

            # TODO: 实现历史数据查询和操纵事件检测
            # 暂时返回空列表
            # 实际使用时需要：
            # 1. 查询历史价格数据
            # 2. 滚动窗口检测暴涨
            # 3. 验证后续回撤
            # 4. 记录事件时间和幅度

            logger.debug(f"检测 {symbol} 的历史操纵事件（{days}天）")

            return events

        except Exception as e:
            logger.error(f"Error detecting manipulation events: {e}")
            return []

    def _calculate_weighted_score(
        self,
        events: List[Dict]
    ) -> float:
        """
        计算时间加权评分

        近期事件权重更高
        """
        if not events:
            return 0.0

        now = datetime.now()
        total_score = 0.0

        for event in events:
            # 计算事件距今天数
            event_time = event.get('timestamp', now)
            days_ago = (now - event_time).days

            # 确定权重
            weight = 0.0
            for days_threshold, w in sorted(self.time_decay.items()):
                if days_ago <= days_threshold:
                    weight = w
                    break

            # 每个事件基础分10分
            total_score += 10 * weight

        return min(70, total_score)  # 基础分最高70分

    async def _calculate_avg_volatility(
        self,
        symbol: str,
        days: int = 30
    ) -> float:
        """
        计算平均日波动率

        波动率 = (最高价 - 最低价) / 开盘价 × 100%
        """
        try:
            # 获取最近30天的日线数据
            # 计算每日波动率
            # 返回平均值

            # TODO: 实现波动率计算
            # 暂时返回0
            return 0.0

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0

    async def _get_avg_volume(
        self,
        symbol: str,
        days: int = 7
    ) -> float:
        """获取平均日成交量（USD）"""
        try:
            # 从Redis获取最近7天的平均成交量
            avg_volume = await redis_client.get_avg_volume(
                'binance',
                symbol,
                minutes=days * 1440
            )
            return avg_volume

        except Exception as e:
            logger.error(f"Error getting avg volume: {e}")
            return 0.0

    async def _calculate_bonus(self, symbol: str) -> float:
        """
        计算加分项

        - 新上市 (<3月): +20分
        - 小市值 (<$50M): +15分
        - 低流动性: +10分
        """
        bonus = 0.0

        try:
            # TODO: 实现加分项计算
            # 需要的数据：
            # 1. 上市时间（从交易所API或数据库）
            # 2. 市值（从CoinGecko API或类似服务）
            # 3. 流动性（订单簿深度）

            # 暂时不计算加分
            pass

        except Exception as e:
            logger.error(f"Error calculating bonus: {e}")

        return bonus

    def _get_manipulation_level(self, score: float) -> str:
        """根据评分确定操纵等级"""
        if score >= 80:
            return 'ULTRA_HIGH'
        elif score >= 60:
            return 'HIGH'
        elif score >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'

    def get_manipulation_coins(
        self,
        min_level: str = 'MEDIUM'
    ) -> List[str]:
        """
        获取妖币列表

        Args:
            min_level: 最低等级 (MEDIUM, HIGH, ULTRA_HIGH)

        Returns:
            符合条件的币种列表
        """
        level_scores = {
            'MEDIUM': 40,
            'HIGH': 60,
            'ULTRA_HIGH': 80
        }

        min_score = level_scores.get(min_level, 40)

        return [
            symbol for symbol, data in self.manipulation_coins.items()
            if data['score'] >= min_score
        ]

    def get_coin_info(self, symbol: str) -> Optional[Dict]:
        """获取指定币种的详细信息"""
        return self.manipulation_coins.get(symbol)

    def is_manipulation_coin(self, symbol: str) -> bool:
        """判断是否为妖币"""
        return symbol in self.manipulation_coins

    def should_update(self) -> bool:
        """判断是否需要更新妖币池"""
        if self.last_update is None:
            return True

        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed >= self.update_interval

    async def get_realtime_score(self, symbol: str) -> Optional[Dict]:
        """
        实时计算币种评分（不等待定期更新）

        用于快速评估新币或可疑币种
        """
        return await self._analyze_symbol(symbol)


# 全局单例
manipulation_detector = ManipulationCoinDetector()
