#!/usr/bin/env python3
"""
测试实时系统性能
验证毫秒级延迟和数据准确性
"""

import asyncio
import time
from datetime import datetime

from src.collectors.binance_realtime_collector import BinanceRealtimeCollector
from src.utils.logger import logger


async def test_latency():
    """测试延迟"""
    logger.info("🧪 Testing Realtime System Latency...")

    collector = BinanceRealtimeCollector()

    # 测试币种
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

    latencies = []

    def on_trade(data):
        """记录延迟"""
        latency = data.get('latency_ms', 0)
        latencies.append(latency)

    # 设置回调
    collector.on_price_update = on_trade

    try:
        # 连接
        await collector.connect()
        logger.info("✅ Connected")

        # 订阅
        await collector.subscribe_symbols(test_symbols)
        logger.info(f"✅ Subscribed to {len(test_symbols)} symbols")

        # 收集10秒数据
        logger.info("📊 Collecting data for 10 seconds...")

        async def listen_task():
            await collector.listen()

        task = asyncio.create_task(listen_task())

        await asyncio.sleep(10)

        # 停止
        task.cancel()
        await collector.disconnect()

        # 分析结果
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)

            logger.info(f"""
╔════════════════════════════════════
║ 📊 Latency Test Results
╠════════════════════════════════════
║ Total Trades: {len(latencies)}
║ Avg Latency: {avg_latency:.1f} ms
║ Min Latency: {min_latency:.1f} ms
║ Max Latency: {max_latency:.1f} ms
║ Trades/sec: {len(latencies) / 10:.1f}
╚════════════════════════════════════
            """)

            if avg_latency < 100:
                logger.info("✅ PASSED: Average latency < 100ms")
            else:
                logger.warning(f"⚠️ WARNING: Average latency {avg_latency:.1f}ms is high")
        else:
            logger.error("❌ FAILED: No trades received")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


async def test_sliding_window():
    """测试滑动窗口性能"""
    logger.info("🧪 Testing Sliding Window Performance...")

    from src.utils.sliding_window import SlidingWindow

    window = SlidingWindow(window_seconds=60)

    # 模拟1000笔交易
    num_trades = 1000
    start_time = time.time()

    base_timestamp = int(datetime.now().timestamp() * 1000)

    for i in range(num_trades):
        window.add_trade(
            price=40000 + i * 0.1,
            quantity=0.01,
            timestamp_ms=base_timestamp + i * 10,  # 每10ms一笔
            is_buyer_maker=(i % 2 == 0)
        )

    add_time = (time.time() - start_time) * 1000  # 毫秒

    # 测试查询性能
    start_time = time.time()

    for _ in range(100):
        metrics = window.get_metrics()

    query_time = (time.time() - start_time) * 1000 / 100  # 平均每次查询时间

    logger.info(f"""
╔════════════════════════════════════
║ 📊 Sliding Window Performance
╠════════════════════════════════════
║ Add {num_trades} trades: {add_time:.2f} ms
║ Per trade: {add_time / num_trades:.3f} ms
║ Query time: {query_time:.2f} ms
║ Metrics: {metrics}
╚════════════════════════════════════
    """)

    if add_time / num_trades < 0.1:
        logger.info("✅ PASSED: Add operation < 0.1ms per trade")
    else:
        logger.warning(f"⚠️ WARNING: Add operation too slow")

    if query_time < 1:
        logger.info("✅ PASSED: Query < 1ms")
    else:
        logger.warning(f"⚠️ WARNING: Query too slow")


async def test_realtime_metrics():
    """测试实时指标计算"""
    logger.info("🧪 Testing Realtime Metrics...")

    collector = BinanceRealtimeCollector()

    test_symbols = ['BTC/USDT']

    try:
        await collector.connect()
        await collector.subscribe_symbols(test_symbols)

        logger.info("📊 Collecting data for 30 seconds...")

        async def listen_task():
            await collector.listen()

        task = asyncio.create_task(listen_task())

        # 每5秒打印一次指标
        for i in range(6):
            await asyncio.sleep(5)

            metrics = await collector.get_realtime_metrics('BTC/USDT', '1m')
            if metrics:
                logger.info(f"""
─────────────────────────────────────
Time: {i * 5}s
Price: ${metrics['close']:,.2f} ({metrics['price_change_pct']:+.2f}%)
Buy/Sell: {metrics['buy_ratio']:.1f}% / {metrics['sell_ratio']:.1f}%
Volume: ${metrics['total_volume']:,.0f}
Trades: {metrics['trade_count']}
Volatility: {metrics['volatility']:.2f}
─────────────────────────────────────
                """)

        task.cancel()
        await collector.disconnect()

        logger.info("✅ Test completed")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


async def main():
    """运行所有测试"""
    logger.info("🚀 Starting Realtime System Tests...")

    # 测试1: 延迟测试
    await test_latency()

    await asyncio.sleep(2)

    # 测试2: 滑动窗口性能
    await test_sliding_window()

    await asyncio.sleep(2)

    # 测试3: 实时指标
    await test_realtime_metrics()

    logger.info("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
