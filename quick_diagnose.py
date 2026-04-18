"""
快速诊断 - 为什么没有警报？

直接检查当前市场状态，看看是否有币种满足触发条件
"""

import asyncio
from src.data_sources.multi_exchange_oi import MultiExchangeOIAggregator
from src.analyzers.manipulation_detector_v2 import ManipulationDetectorV2
from src.utils.logger import logger


async def quick_check():
    """快速检查前 20 个热门币种"""

    # 热门币种
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
        'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT',
        'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'ETC/USDT',
        'WIF/USDT', 'PEPE/USDT', 'BONK/USDT', 'FLOKI/USDT', 'SHIB/USDT'
    ]

    oi_aggregator = MultiExchangeOIAggregator()
    detector = ManipulationDetectorV2()

    logger.info("="*60)
    logger.info("🔍 快速诊断 - 检查是否有币种满足触发条件")
    logger.info("="*60)

    success_count = 0
    fail_count = 0
    high_risk_count = 0

    for symbol in symbols:
        try:
            # 获取 OI 数据
            oi_data = await oi_aggregator.get_aggregated_oi(symbol)

            if not oi_data:
                fail_count += 1
                logger.warning(f"❌ {symbol}: 无法获取 OI 数据")
                continue

            # 模拟市场数据
            market_data = {
                'binance_oi': oi_data['binance_oi'],
                'total_oi': oi_data['total_oi'],
                'volume_24h': oi_data['binance_oi'] * 5,  # 假设 vol=5x OI
                'volatility_24h': 0.15,
                'funding_rate': 0.0001
            }

            # 计算操纵评分
            score = await detector.calculate_manipulation_score(symbol, market_data)

            if score:
                success_count += 1
                status = "🔴高风险" if score.score >= 50 else "🟢正常"

                if score.score >= 50:
                    high_risk_count += 1

                logger.info(
                    f"{status} {symbol}: "
                    f"评分={score.score}, "
                    f"Binance占比={score.binance_oi_ratio:.1%}, "
                    f"vol/OI={score.vol_oi_ratio:.1f}x"
                )
            else:
                fail_count += 1
                logger.warning(f"❌ {symbol}: 被过滤（刷量或数据异常）")

            await asyncio.sleep(0.3)  # 避免限流

        except Exception as e:
            fail_count += 1
            logger.error(f"❌ {symbol}: {e}")

    logger.info("="*60)
    logger.info(f"✅ 诊断完成")
    logger.info(f"   - 成功: {success_count}/{len(symbols)}")
    logger.info(f"   - 失败: {fail_count}/{len(symbols)}")
    logger.info(f"   - 高风险币种（评分≥50）: {high_risk_count}")
    logger.info("="*60)

    if high_risk_count == 0:
        logger.info("💡 结论：当前市场没有明显的高风险妖币")
        logger.info("   这可能就是昨晚没有警报的原因")
    else:
        logger.info(f"💡 结论：当前有 {high_risk_count} 个高风险币种")
        logger.info("   如果系统正常运行但无警报，说明市场条件未满足（价格、买卖比等）")


if __name__ == "__main__":
    asyncio.run(quick_check())
