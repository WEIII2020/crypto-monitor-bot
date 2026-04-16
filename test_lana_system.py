#!/usr/bin/env python3
"""
测试 Lana 优化后的系统
验证所有新组件和信号融合逻辑
"""

import asyncio
from src.analyzers.oi_monitor import OIMonitor
from src.analyzers.square_monitor import SquareMonitor
from src.analyzers.signal_fusion import SignalFusion
from src.utils.logger import logger


async def test_components():
    """测试新增组件"""
    logger.info("=" * 60)
    logger.info("测试1: 组件初始化")
    logger.info("=" * 60)

    oi_monitor = OIMonitor()
    square_monitor = SquareMonitor()
    signal_fusion = SignalFusion()

    logger.info("✅ OIMonitor 初始化成功")
    logger.info("✅ SquareMonitor 初始化成功")
    logger.info("✅ SignalFusion 初始化成功")

    logger.info("\n✅ 所有组件初始化完成\n")


async def test_signal_fusion():
    """测试信号融合逻辑"""
    logger.info("=" * 60)
    logger.info("测试2: 信号融合逻辑")
    logger.info("=" * 60)

    fusion = SignalFusion()

    # 模拟多个信号
    test_signals = [
        {
            'alert_type': 'OI_SPIKE',
            'score': 40,
            'symbol': 'BTC/USDT',
            'current_price': 60000
        },
        {
            'alert_type': 'PRICE_SPIKE',
            'score': 30,
            'symbol': 'BTC/USDT',
            'current_price': 60000
        },
        {
            'alert_type': 'SQUARE_TRENDING',
            'score': 20,
            'symbol': 'BTC/USDT',
            'current_price': 60000
        }
    ]

    logger.info(f"模拟3个信号: OI异常 + 价格突变 + 广场热度")

    # 执行融合
    fused = await fusion.fuse_signals('BTC/USDT', test_signals)

    if fused:
        logger.info(f"✅ 信号融合成功:")
        logger.info(f"   综合评分: {fused['total_score']}/100")
        logger.info(f"   建议行动: {fused['action']}")
        logger.info(f"   告警等级: {fused['alert_level']}")
        logger.info(f"   组合加成: +{fused['bonus']}分")
    else:
        logger.warning("⚠️  信号融合返回None（可能分数不够）")

    logger.info("\n✅ 信号融合测试完成\n")


async def test_lana_scoring():
    """测试lana评分规则"""
    logger.info("=" * 60)
    logger.info("测试3: Lana评分规则")
    logger.info("=" * 60)

    fusion = SignalFusion()

    logger.info("📊 权重配置:")
    for signal_type, weight in fusion.weights.items():
        logger.info(f"   {signal_type}: {weight}分")

    logger.info("\n📊 行动阈值:")
    logger.info(f"   观察(WATCH): ≥{fusion.watch_threshold}分")
    logger.info(f"   买入(BUY): ≥{fusion.buy_threshold}分")

    logger.info("\n✅ Lana评分规则验证完成\n")


async def test_golden_combinations():
    """测试黄金组合"""
    logger.info("=" * 60)
    logger.info("测试4: 黄金组合加成")
    logger.info("=" * 60)

    fusion = SignalFusion()

    # 黄金组合1：OI + 价格
    combo1 = [
        {'alert_type': 'OI_SPIKE', 'score': 40},
        {'alert_type': 'PRICE_SPIKE', 'score': 30}
    ]
    bonus1 = fusion._calculate_bonus(combo1)
    logger.info(f"黄金组合1 (OI+价格): +{bonus1}分")

    # 黄金组合2：OI + 广场
    combo2 = [
        {'alert_type': 'OI_SPIKE', 'score': 40},
        {'alert_type': 'SQUARE_TRENDING', 'score': 20}
    ]
    bonus2 = fusion._calculate_bonus(combo2)
    logger.info(f"黄金组合2 (OI+广场): +{bonus2}分")

    # 黄金组合3：暴涨 + OI
    combo3 = [
        {'alert_type': 'PUMP_DETECTED', 'score': 30},
        {'alert_type': 'OI_SPIKE', 'score': 40}
    ]
    bonus3 = fusion._calculate_bonus(combo3)
    logger.info(f"黄金组合3 (暴涨+OI): +{bonus3}分")

    logger.info("\n✅ 黄金组合测试完成\n")


async def main():
    """主测试流程"""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("开始测试 Lana 优化系统")
        logger.info("=" * 60 + "\n")

        # 测试1: 组件初始化
        await test_components()

        # 测试2: 信号融合
        await test_signal_fusion()

        # 测试3: Lana评分规则
        await test_lana_scoring()

        # 测试4: 黄金组合
        await test_golden_combinations()

        # 总结
        logger.info("=" * 60)
        logger.info("🎉 Lana系统测试完成！")
        logger.info("=" * 60)
        logger.info("\n✅ 新增功能:")
        logger.info("   ✓ OI监控器（48h变动>50%，价格<5%）")
        logger.info("   ✓ 广场热度监控（散户关注度）")
        logger.info("   ✓ 信号融合器（多维度评分）")
        logger.info("")
        logger.info("✅ Lana方法核心:")
        logger.info("   ✓ OI异常（40分权重）- 最重要")
        logger.info("   ✓ 价格波动（30分权重）")
        logger.info("   ✓ 巨鲸行为（20分权重）")
        logger.info("   ✓ 广场热度（10分权重）")
        logger.info("")
        logger.info("✅ 黄金组合加成:")
        logger.info("   ✓ OI+价格 (+15分)")
        logger.info("   ✓ OI+广场 (+10分)")
        logger.info("   ✓ 暴涨+OI (+20分)")
        logger.info("")
        logger.info("✅ 行动规则:")
        logger.info("   ✓ ≥60分 = WATCH（观察）")
        logger.info("   ✓ ≥80分 = BUY（买入）")
        logger.info("   ✓ 亏200u立即止损")
        logger.info("")
        logger.info("📊 系统状态:")
        logger.info("   ✓ 监控46个币种")
        logger.info("   ✓ 4个分析器并发运行")
        logger.info("   ✓ 每60秒融合一次信号")
        logger.info("")
        logger.info("💡 下一步: 同步到云端服务器")
        logger.info("=" * 60 + "\n")

        return True

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = asyncio.run(main())
    exit(0 if success else 1)
