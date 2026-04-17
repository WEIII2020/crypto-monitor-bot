#!/usr/bin/env python3
"""
Crypto Monitor Bot - Phase 2
交易信号生成系统（做多/做空 + 妖币策略）

功能：
- Phase 1: 毫秒级实时数据采集
- Phase 2: V4A/V7/V8 妖币策略 + 做多/做空双向信号
- 自动 Telegram 推送
"""

import asyncio
import signal
import sys
from typing import Set, Dict, Optional
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.symbol_selector import SymbolSelector
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.collectors.binance_realtime_collector import BinanceRealtimeCollector
from src.analyzers.trading_signal_generator import TradingSignalGenerator
from src.notifiers.telegram_notifier import TelegramNotifier


class CryptoMonitorBotPhase2:
    """Phase 2 交易信号系统"""

    def __init__(self):
        self.running = False
        self.tasks: Set[asyncio.Task] = set()

        # Phase 1 组件
        self.collector = BinanceRealtimeCollector()
        self.symbol_selector = SymbolSelector()

        # Phase 2 组件
        self.signal_generator = TradingSignalGenerator()
        self.notifier = TelegramNotifier()

        # 监控配置
        self.test_mode = False  # False = 200币种，True = 5币种测试
        self.symbols = []

        # 历史数据缓存（用于 V7 等策略）
        self.price_history = {}  # {symbol: [(timestamp, price), ...]}
        self.oi_history = {}     # {symbol: [(timestamp, oi), ...]}

        # 性能统计
        self.stats = {
            'total_signals': 0,
            'v4a_signals': 0,
            'v7_signals': 0,
            'v8_signals': 0,
            'long_signals': 0,
            'signals_sent': 0
        }

    async def start(self):
        """启动 Phase 2 系统"""
        logger.info("🚀 Starting Phase 2 Trading Signal System...")

        try:
            # 连接数据库
            await redis_client.connect()
            await postgres_client.connect()
            logger.info("✅ Database connections established")

            # 选择监控币种
            if self.test_mode:
                self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
                logger.info(f"🧪 Test mode: monitoring {len(self.symbols)} symbols")
            else:
                logger.info("📊 Selecting optimal symbols...")
                self.symbols = await self.symbol_selector.get_monitoring_list(max_symbols=200)
                logger.info(f"✅ Selected {len(self.symbols)} symbols")

            # 连接 Binance
            success = await self.collector.connect_with_retry()
            if not success:
                logger.error("❌ Failed to connect to Binance")
                return

            # 订阅实时数据
            await self.collector.subscribe_symbols(self.symbols)
            logger.info(f"✅ Subscribed to {len(self.symbols)} symbols")

            self.running = True

            # 启动后台任务
            collector_task = asyncio.create_task(self._run_collector())
            signal_task = asyncio.create_task(self._run_signal_generation())
            oi_task = asyncio.create_task(self._run_oi_collection())
            stats_task = asyncio.create_task(self._run_stats_monitor())

            self.tasks.add(collector_task)
            self.tasks.add(signal_task)
            self.tasks.add(oi_task)
            self.tasks.add(stats_task)

            # 设置价格历史回调
            self.collector.on_price_update = self._cache_price_history

            logger.info("✅ Phase 2 system is running! Press Ctrl+C to stop.")

            # 冷启动提示
            logger.info("⏳ 冷启动期说明：")
            logger.info("   • V4A 策略：立即可用（需要实时数据）")
            logger.info("   • V8 策略：30 分钟后可用（需要 30min OI 历史）")
            logger.info("   • LONG 策略：1 小时后可用（需要 1h OI 历史）")
            logger.info("   • V7 策略：4 小时后可用（需要 4h 价格和 OI 历史）")
            logger.info("   📊 系统正在积累历史数据，请耐心等待...")

            await asyncio.gather(*self.tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Error starting Phase 2: {e}")
            await self.stop()

    async def stop(self):
        """停止系统"""
        logger.info("🛑 Stopping Phase 2 system...")
        self.running = False

        for task in self.tasks:
            if not task.done():
                task.cancel()

        await self.collector.disconnect()
        await redis_client.disconnect()
        await postgres_client.disconnect()

        logger.info("✅ Phase 2 stopped successfully")

    async def _run_collector(self):
        """运行数据采集器"""
        try:
            await self.collector.listen()
        except asyncio.CancelledError:
            logger.info("Collector task cancelled")
        except Exception as e:
            logger.error(f"Collector error: {e}")

    async def _run_signal_generation(self):
        """信号生成主循环（并行版）"""
        logger.info("🔍 Starting signal generation...")

        check_interval = 5  # 每 5 秒检查一次

        try:
            while self.running:
                # 并行检查所有币种
                tasks = [
                    self._check_trading_signals(symbol)
                    for symbol in self.symbols
                ]

                # 使用 gather 并捕获异常
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 记录错误（不中断）
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error checking {self.symbols[i]}: {result}")

                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("Signal generation task cancelled")
        except Exception as e:
            logger.error(f"Signal generation error: {e}")

    async def _check_trading_signals(self, symbol: str):
        """检查交易信号"""
        try:
            # 1. 获取实时数据（Phase 1）
            realtime_data = await self._get_realtime_data(symbol)
            if not realtime_data:
                return

            # 2. 获取历史数据（用于 V7 等）
            historical_data = await self._get_historical_data(symbol)

            # 3. 获取市场数据（OI、资金费率等）
            market_data = await self._get_market_data(symbol)

            # 4. 合并数据（V8/LONG 需要的字段传递给 realtime_data）
            realtime_data['oi_30m_ago'] = historical_data.get('oi_30m_ago')
            realtime_data['current_oi'] = historical_data.get('current_oi')
            realtime_data['oi_change_1h'] = historical_data.get('oi_change_1h')

            # 5. 生成信号
            signals = await self.signal_generator.generate_signals(
                symbol,
                realtime_data,
                historical_data,
                market_data
            )

            # 6. 处理信号
            for signal in signals:
                await self._handle_signal(signal)

        except Exception as e:
            logger.error(f"Error checking signals for {symbol}: {e}")

    async def _get_realtime_data(self, symbol: str) -> Dict:
        """获取实时数据（Phase 1 提供）"""
        # 从 Phase 1 的滑动窗口获取
        metrics_1m = await self.collector.get_realtime_metrics(symbol, '1m')
        kline_1m = await self.collector.get_kline(symbol, '1m')
        kline_1h = await self.collector.get_kline(symbol, '1h')

        return {
            'metrics': metrics_1m,
            'kline_1m': kline_1m,
            'kline_1h': kline_1h
        }

    async def _get_historical_data(self, symbol: str) -> Dict:
        """获取历史数据"""
        now = datetime.now()

        # 获取各时间点的历史数据
        four_hours_ago = now - timedelta(hours=4)
        one_hour_ago = now - timedelta(hours=1)
        thirty_min_ago = now - timedelta(minutes=30)

        # 价格历史
        price_4h_ago = await self._get_cached_price(symbol, four_hours_ago)

        # OI 历史
        oi_4h_ago = await self._get_cached_oi(symbol, four_hours_ago)
        oi_1h_ago = await self._get_cached_oi(symbol, one_hour_ago)
        oi_30m_ago = await self._get_cached_oi(symbol, thirty_min_ago)

        # 当前数据
        current_metrics = await self.collector.get_realtime_metrics(symbol, '1m')
        current_price = current_metrics['close'] if current_metrics else None

        # 当前 OI（从最新记录）
        current_oi = None
        if symbol in self.oi_history and self.oi_history[symbol]:
            current_oi = self.oi_history[symbol][-1][1]

        # 计算 OI 变化率
        oi_change_1h = 0
        if oi_1h_ago and current_oi and oi_1h_ago > 0:
            oi_change_1h = (current_oi - oi_1h_ago) / oi_1h_ago

        return {
            'price_4h_ago': price_4h_ago,
            'oi_4h_ago': oi_4h_ago,
            'current_price': current_price,
            'current_oi': current_oi,
            'oi_30m_ago': oi_30m_ago,
            'oi_change_1h': oi_change_1h,
        }

    async def _get_market_data(self, symbol: str) -> Dict:
        """获取市场数据（OI、资金费率等）"""
        import aiohttp

        binance_symbol = symbol.replace('/', '')

        try:
            async with aiohttp.ClientSession() as session:
                # 1. 获取当前价格（用于 OI 转换）
                ticker_url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                async with session.get(ticker_url, params={'symbol': binance_symbol}, timeout=5) as resp:
                    if resp.status != 200:
                        raise Exception(f"Ticker API error: {resp.status}")
                    ticker_data = await resp.json()
                    current_price = float(ticker_data['lastPrice'])
                    volume_24h = float(ticker_data['quoteVolume'])
                    price_change_pct = abs(float(ticker_data['priceChangePercent'])) / 100

                # 2. 获取 Binance OI（合约数量）
                oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
                async with session.get(oi_url, params={'symbol': binance_symbol}, timeout=5) as resp:
                    if resp.status != 200:
                        raise Exception(f"OI API error: {resp.status}")
                    oi_data = await resp.json()
                    oi_contracts = float(oi_data['openInterest'])
                    binance_oi = oi_contracts * current_price  # 转换为 USD

                # 3. 获取资金费率
                funding_url = "https://fapi.binance.com/fapi/v1/premiumIndex"
                async with session.get(funding_url, params={'symbol': binance_symbol}, timeout=5) as resp:
                    if resp.status != 200:
                        raise Exception(f"Funding API error: {resp.status}")
                    funding_data = await resp.json()
                    funding_rate = float(funding_data['lastFundingRate'])

                # 4. 估算总 OI（Binance 通常占 40-60%，保守估计 50%）
                total_oi = binance_oi * 2

                return {
                    'binance_oi': binance_oi,
                    'total_oi': total_oi,
                    'volume_24h': volume_24h,
                    'volatility_24h': price_change_pct,
                    'funding_rate': funding_rate,
                }

        except Exception as e:
            logger.warning(f"Error fetching market data for {symbol}: {e}, using fallback")
            # 返回安全的默认值（不会触发信号）
            return {
                'binance_oi': 0,
                'total_oi': 0,
                'volume_24h': 0,
                'volatility_24h': 0,
                'funding_rate': 0,
            }

    async def _get_cached_price(self, symbol: str, timestamp: datetime) -> float:
        """从缓存获取历史价格"""
        # 简化实现
        if symbol not in self.price_history:
            return None

        # 查找最接近的价格
        for ts, price in reversed(self.price_history[symbol]):
            if ts <= timestamp:
                return price

        return None

    async def _get_cached_oi(self, symbol: str, timestamp: datetime) -> float:
        """从缓存获取历史 OI"""
        # 简化实现
        if symbol not in self.oi_history:
            return None

        for ts, oi in reversed(self.oi_history[symbol]):
            if ts <= timestamp:
                return oi

        return None

    async def _cache_price_history(self, price_data: Dict):
        """缓存价格历史（回调函数）"""
        try:
            symbol = price_data['symbol']
            price = price_data['price']
            timestamp = datetime.fromtimestamp(price_data['timestamp'])

            if symbol not in self.price_history:
                self.price_history[symbol] = []

            self.price_history[symbol].append((timestamp, price))

            # 只保留 6 小时的数据
            cutoff = datetime.now() - timedelta(hours=6)
            self.price_history[symbol] = [
                (ts, val) for ts, val in self.price_history[symbol]
                if ts > cutoff
            ]
        except Exception as e:
            logger.error(f"Error caching price history: {e}")

    async def _run_oi_collection(self):
        """定期采集 OI 数据"""
        logger.info("📊 Starting OI collection...")

        interval = 60  # 每 60 秒采集一次

        try:
            while self.running:
                for symbol in self.symbols:
                    try:
                        # 从 Binance API 获取 OI
                        oi = await self._fetch_binance_oi(symbol)

                        if oi is not None:
                            # 存储到历史记录
                            now = datetime.now()
                            if symbol not in self.oi_history:
                                self.oi_history[symbol] = []

                            self.oi_history[symbol].append((now, oi))

                            # 只保留 6 小时的数据
                            cutoff = now - timedelta(hours=6)
                            self.oi_history[symbol] = [
                                (ts, val) for ts, val in self.oi_history[symbol]
                                if ts > cutoff
                            ]

                    except Exception as e:
                        logger.debug(f"Error fetching OI for {symbol}: {e}")

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info("OI collection task cancelled")
        except Exception as e:
            logger.error(f"OI collection error: {e}")

    async def _fetch_binance_oi(self, symbol: str) -> Optional[float]:
        """从 Binance API 获取当前 OI"""
        import aiohttp

        binance_symbol = symbol.replace('/', '')

        try:
            async with aiohttp.ClientSession() as session:
                # 获取当前价格
                ticker_url = "https://fapi.binance.com/fapi/v1/ticker/price"
                async with session.get(ticker_url, params={'symbol': binance_symbol}, timeout=5) as resp:
                    if resp.status != 200:
                        return None
                    price_data = await resp.json()
                    current_price = float(price_data['price'])

                # 获取 OI（合约数量）
                oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
                async with session.get(oi_url, params={'symbol': binance_symbol}, timeout=5) as resp:
                    if resp.status != 200:
                        return None
                    oi_data = await resp.json()
                    oi_contracts = float(oi_data['openInterest'])

                    # 转换为 USD
                    return oi_contracts * current_price

        except Exception as e:
            logger.debug(f"Error fetching OI for {symbol}: {e}")
            return None

    async def _handle_signal(self, signal):
        """处理信号"""
        # 更新统计
        self.stats['total_signals'] += 1

        if signal.strategy == 'V4A_SHORT':
            self.stats['v4a_signals'] += 1
        elif signal.strategy == 'V7_SHORT':
            self.stats['v7_signals'] += 1
        elif signal.strategy == 'V8_SHORT':
            self.stats['v8_signals'] += 1
        elif signal.strategy == 'LONG':
            self.stats['long_signals'] += 1

        # 格式化消息
        message = self.signal_generator.format_telegram_message(signal)

        # 日志输出（使用 info 级别，信号是正常事件）
        logger.info(f"\n{'='*50}")
        logger.info(f"🎯 NEW SIGNAL: {signal.symbol} - {signal.strategy}")
        logger.info(message)
        logger.info(f"{'='*50}\n")

        # 发送 Telegram 通知
        try:
            await self.notifier.send_message(message)
            self.stats['signals_sent'] += 1
            logger.info(f"✅ Signal sent to Telegram: {signal.symbol}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram: {e}")

    async def _run_stats_monitor(self):
        """性能监控"""
        logger.info("📈 Starting stats monitor...")

        interval = 60  # 每 60 秒报告一次

        try:
            while self.running:
                await asyncio.sleep(interval)

                # 获取 Phase 1 性能
                collector_stats = self.collector.get_performance_stats()

                # 获取 Phase 2 信号统计
                logger.info(
                    f"📊 Phase 2 Stats: "
                    f"{self.stats['total_signals']} signals "
                    f"(V4A:{self.stats['v4a_signals']}, "
                    f"V7:{self.stats['v7_signals']}, "
                    f"V8:{self.stats['v8_signals']}, "
                    f"LONG:{self.stats['long_signals']}) | "
                    f"Sent: {self.stats['signals_sent']}"
                )

                logger.info(
                    f"📊 Phase 1 Stats: "
                    f"{collector_stats['trades_per_second']} trades/s, "
                    f"{collector_stats['avg_latency_ms']}ms latency"
                )

                # 策略状态报告（每 5 分钟）
                from datetime import datetime
                now = datetime.now()
                if int(now.timestamp()) % 300 < 60:  # 每 5 分钟
                    # 统计有历史数据的币种数
                    price_history_count = len(self.price_history)
                    oi_history_count = len(self.oi_history)

                    logger.info(
                        f"📈 历史数据状态: "
                        f"价格历史={price_history_count}币种, "
                        f"OI历史={oi_history_count}币种"
                    )

                    # 检查策略可用性
                    v4a_ready = True  # V4A 只需实时数据
                    v8_ready = any(
                        len(history) >= 2 for history in self.oi_history.values()
                    )  # 至少 2 个 OI 数据点（30min）
                    long_ready = any(
                        len(history) >= 2 for history in self.oi_history.values()
                    )  # 至少 2 个 OI 数据点（1h）
                    v7_ready = (
                        any(len(history) >= 5 for history in self.price_history.values()) and
                        any(len(history) >= 5 for history in self.oi_history.values())
                    )  # 至少 5 个数据点（4h）

                    logger.info(
                        f"🎯 策略状态: "
                        f"V4A={'✅' if v4a_ready else '⏳'}, "
                        f"V8={'✅' if v8_ready else '⏳'}, "
                        f"LONG={'✅' if long_ready else '⏳'}, "
                        f"V7={'✅' if v7_ready else '⏳'}"
                    )

        except asyncio.CancelledError:
            logger.info("Stats monitor task cancelled")


async def main():
    """主函数"""
    bot = CryptoMonitorBotPhase2()

    def signal_handler(signum, frame):
        logger.info("Received interrupt signal")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Phase 2 stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
