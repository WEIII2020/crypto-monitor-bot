# 🎯 适用于 Crypto Monitor Bot 的技能提取

**生成时间**: 2026-04-17  
**目标**: 仅提取可直接应用到现有bot的功能模块

---

## 📋 **你的Bot当前架构**

```python
crypto-monitor-bot/
├── main_phase2.py                    # Phase 2 交易信号系统
├── hermes_integration/
│   ├── lana_trading_engine.py       # Lana规则引擎
│   ├── telegram_commands.py         # Telegram命令
│   └── monitor_data_reader.py
├── src/
│   ├── collectors/                   # Binance实时数据采集
│   ├── analyzers/                    # 信号分析器
│   ├── notifiers/                    # Telegram通知
│   └── database/                     # Redis + PostgreSQL
└── tests/
```

**核心能力**:
- ✅ 实时数据采集 (Binance WebSocket)
- ✅ 信号生成 (V4A/V7/V8策略)
- ✅ Telegram通知
- ✅ Lana规则引擎 (200 USDT止损, 1小时持仓)
- ❌ **缺少**: 自动下单、风险检查、订单管理

---

## 🚀 **可直接应用的模块 (优先级排序)**

### **P0 - 立即可用 (本周)** 🔥

#### **1. 自动交易执行模块**

**来源**: OKX Trade Kit - `spot-trade.ts` + Gate - `gate-exchange-spot`

**为什么需要**: 你的bot已经生成信号，但需要手动交易。自动化执行可实现闭环。

**实现方案**:
```python
# crypto-monitor-bot/src/trading/spot_executor.py

import ccxt
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class OrderResult:
    """订单执行结果"""
    order_id: str
    symbol: str
    side: str          # 'buy' | 'sell'
    type: str          # 'market' | 'limit'
    price: float
    amount: float
    filled: float
    status: str        # 'open' | 'closed' | 'canceled'
    cost: float        # 实际成本 (USDT)
    fee: float


class SpotTradeExecutor:
    """现货交易执行器 - 适配你的Lana引擎"""
    
    def __init__(
        self, 
        exchange_name: str = 'binance',  # 或 'okx', 'gate'
        api_key: str = None,
        api_secret: str = None,
        testnet: bool = True  # 默认测试网
    ):
        """
        初始化交易执行器
        
        Args:
            exchange_name: 交易所名称
            testnet: 是否使用测试网 (建议先测试)
        """
        self.exchange_name = exchange_name
        
        # 初始化 CCXT 交易所
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # 自动限速
            'options': {
                'defaultType': 'spot',  # 现货交易
                'adjustForTimeDifference': True
            }
        })
        
        if testnet:
            self.exchange.set_sandbox_mode(True)
    
    async def place_market_order(
        self,
        symbol: str,      # 'BTC/USDT'
        side: str,        # 'buy' | 'sell'
        amount_usdt: float,  # 用多少USDT买入
        max_slippage: float = 0.005  # 最大滑点 0.5%
    ) -> Optional[OrderResult]:
        """
        下市价单 (Lana策略专用)
        
        特点:
        - 自动计算数量
        - 滑点保护
        - 立即成交
        
        Example:
            # 买入100 USDT的BTC
            result = await executor.place_market_order(
                symbol='BTC/USDT',
                side='buy',
                amount_usdt=100
            )
        """
        try:
            # 1. 获取当前市场价格
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # 2. 计算买入数量
            if side == 'buy':
                amount = amount_usdt / current_price
            else:  # sell
                amount = amount_usdt / current_price
            
            # 3. 滑点检查 (可选)
            orderbook = await self.exchange.fetch_order_book(symbol, limit=5)
            expected_price = self._calculate_expected_price(
                orderbook, side, amount
            )
            actual_slippage = abs(expected_price - current_price) / current_price
            
            if actual_slippage > max_slippage:
                logger.warning(f"⚠️ 滑点过大: {actual_slippage:.2%} > {max_slippage:.2%}")
                return None
            
            # 4. 下单
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount
            )
            
            # 5. 等待订单成交
            filled_order = await self._wait_for_fill(order['id'], symbol)
            
            # 6. 返回结果
            return OrderResult(
                order_id=filled_order['id'],
                symbol=symbol,
                side=side,
                type='market',
                price=filled_order['average'],
                amount=filled_order['filled'],
                filled=filled_order['filled'],
                status=filled_order['status'],
                cost=filled_order['cost'],
                fee=filled_order.get('fee', {}).get('cost', 0)
            )
            
        except Exception as e:
            logger.error(f"❌ 下单失败: {symbol} {side} {amount_usdt}U - {e}")
            return None
    
    async def place_stop_loss_order(
        self,
        symbol: str,
        side: str,         # 'sell' (平仓)
        amount: float,     # 持仓数量
        stop_price: float, # 触发价格
        limit_price: float = None  # 限价 (可选)
    ) -> Optional[OrderResult]:
        """
        下止损单 (Lana规则: 200 USDT止损)
        
        Example:
            # BTC止损单: 价格跌破60000立即卖出
            result = await executor.place_stop_loss_order(
                symbol='BTC/USDT',
                side='sell',
                amount=0.01,
                stop_price=60000
            )
        """
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type='stop_loss' if not limit_price else 'stop_loss_limit',
                side=side,
                amount=amount,
                price=limit_price,
                params={'stopPrice': stop_price}
            )
            
            return OrderResult(
                order_id=order['id'],
                symbol=symbol,
                side=side,
                type='stop_loss',
                price=stop_price,
                amount=amount,
                filled=0,
                status='open',
                cost=0,
                fee=0
            )
            
        except Exception as e:
            logger.error(f"❌ 止损单失败: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消订单"""
        try:
            await self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            logger.error(f"❌ 取消订单失败: {e}")
            return False
    
    async def get_balance(self, currency: str = 'USDT') -> float:
        """获取余额"""
        try:
            balance = await self.exchange.fetch_balance()
            return balance.get(currency, {}).get('free', 0)
        except Exception as e:
            logger.error(f"❌ 获取余额失败: {e}")
            return 0
    
    def _calculate_expected_price(
        self, 
        orderbook: dict, 
        side: str, 
        amount: float
    ) -> float:
        """计算预期成交价格 (考虑订单簿深度)"""
        if side == 'buy':
            asks = orderbook['asks']
            remaining = amount
            total_cost = 0
            
            for price, qty in asks:
                if remaining <= 0:
                    break
                fill_qty = min(remaining, qty)
                total_cost += fill_qty * price
                remaining -= fill_qty
            
            return total_cost / amount if amount > 0 else asks[0][0]
        else:
            bids = orderbook['bids']
            remaining = amount
            total_revenue = 0
            
            for price, qty in bids:
                if remaining <= 0:
                    break
                fill_qty = min(remaining, qty)
                total_revenue += fill_qty * price
                remaining -= fill_qty
            
            return total_revenue / amount if amount > 0 else bids[0][0]
    
    async def _wait_for_fill(
        self, 
        order_id: str, 
        symbol: str, 
        timeout: int = 30
    ) -> dict:
        """等待订单成交"""
        for _ in range(timeout):
            order = await self.exchange.fetch_order(order_id, symbol)
            if order['status'] in ['closed', 'canceled']:
                return order
            await asyncio.sleep(1)
        
        raise TimeoutError(f"订单 {order_id} 超时未成交")
```

**集成到Lana引擎**:
```python
# 修改 hermes_integration/lana_trading_engine.py

from src.trading.spot_executor import SpotTradeExecutor, OrderResult

class LanaRuleEngine:
    
    def __init__(self):
        # ... 现有代码 ...
        
        # 添加交易执行器
        self.executor = SpotTradeExecutor(
            exchange_name='binance',
            testnet=True  # ⚠️ 先用测试网！
        )
    
    async def execute_signal(self, signal: Dict) -> Optional[Position]:
        """
        执行交易信号 (自动化闭环)
        
        流程:
        1. 检查信号质量
        2. 检查余额
        3. 下单
        4. 设置止损
        5. 记录持仓
        """
        # 1. 信号质量检查 (已有)
        if not self.check_signal_quality(signal):
            return None
        
        # 2. 检查余额
        balance = await self.executor.get_balance('USDT')
        if balance < self.position_size_usdt:
            logger.warning(f"⚠️ 余额不足: {balance} < {self.position_size_usdt}")
            return None
        
        # 3. 下单
        symbol = signal['symbol']
        action = signal['action']
        
        order_result = await self.executor.place_market_order(
            symbol=symbol,
            side='buy' if action == 'BUY' else 'sell',
            amount_usdt=self.position_size_usdt,
            max_slippage=0.005  # 0.5%滑点限制
        )
        
        if not order_result:
            logger.error(f"❌ 下单失败: {symbol}")
            return None
        
        logger.info(f"✅ 订单成交: {symbol} {order_result.side} "
                   f"{order_result.filled}@{order_result.price}")
        
        # 4. 计算止损价格 (Lana规则: 200 USDT止损)
        stop_loss_pct = self.max_loss_usdt / self.position_size_usdt
        stop_loss_price = order_result.price * (1 - stop_loss_pct) \
            if action == 'BUY' else order_result.price * (1 + stop_loss_pct)
        
        # 5. 设置止损单
        stop_order = await self.executor.place_stop_loss_order(
            symbol=symbol,
            side='sell' if action == 'BUY' else 'buy',
            amount=order_result.filled,
            stop_price=stop_loss_price
        )
        
        if stop_order:
            logger.info(f"✅ 止损单已设置: {stop_loss_price}")
        
        # 6. 记录持仓
        position = Position(
            symbol=symbol,
            entry_price=order_result.price,
            entry_time=datetime.now(),
            size=order_result.cost,
            stop_loss_price=stop_loss_price,
            target_profit_price=None,  # Lana不设目标价
            status=PositionStatus.OPEN
        )
        
        self.positions[symbol] = position
        
        return position
```

**测试命令**:
```bash
# 1. 先在测试网测试
python -c "
from src.trading.spot_executor import SpotTradeExecutor
import asyncio

async def test():
    executor = SpotTradeExecutor(testnet=True)
    
    # 获取余额
    balance = await executor.get_balance('USDT')
    print(f'余额: {balance} USDT')
    
    # 测试下单 (测试网不会真实扣款)
    result = await executor.place_market_order(
        symbol='BTC/USDT',
        side='buy',
        amount_usdt=100
    )
    print(f'订单结果: {result}')

asyncio.run(test())
"

# 2. 确认无误后，切换到真实交易
# 修改 lana_trading_engine.py 中的 testnet=False
```

---

#### **2. 风险检查模块** (30+维度)

**来源**: Gate - `gate-info-riskcheck`

**为什么需要**: 防止交易诈骗币、高税币、低流动性币。

**实现方案**:
```python
# crypto-monitor-bot/src/risk/risk_checker.py

import aiohttp
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class RiskReport:
    """风险评估报告"""
    symbol: str
    risk_score: float  # 0-100, 100=最安全
    rating: str        # A/B/C/D/F
    warnings: List[str]
    checks: Dict[str, dict]
    is_safe: bool      # 是否可以交易


class TokenRiskChecker:
    """代币风险检查器 (30+维度)"""
    
    def __init__(self):
        self.min_safe_score = 60  # 低于60分禁止交易
    
    async def check_token(self, symbol: str) -> RiskReport:
        """
        全面风险检查
        
        检查项:
        1. Honeypot检测 (Critical)
        2. 买卖税分析
        3. 流动性深度
        4. 持仓集中度
        5. 合约审计状态
        6. 代币年龄
        """
        checks = {}
        warnings = []
        
        # 1. Honeypot检测 (使用 honeypot.is API)
        honeypot_result = await self._check_honeypot(symbol)
        checks['honeypot'] = honeypot_result
        
        if honeypot_result['is_honeypot']:
            warnings.append("🚨 CRITICAL: Honeypot检测 - 禁止交易!")
            return RiskReport(
                symbol=symbol,
                risk_score=0,
                rating='F',
                warnings=warnings,
                checks=checks,
                is_safe=False
            )
        
        # 2. 税率检查
        tax_result = await self._check_tax(symbol)
        checks['tax'] = tax_result
        
        if tax_result['buy_tax'] > 10 or tax_result['sell_tax'] > 10:
            warnings.append(
                f"⚠️ 高税率: 买入{tax_result['buy_tax']}% / "
                f"卖出{tax_result['sell_tax']}%"
            )
        
        # 3. 流动性检查
        liquidity_result = await self._check_liquidity(symbol)
        checks['liquidity'] = liquidity_result
        
        if liquidity_result['usd_value'] < 100000:
            warnings.append(
                f"⚠️ 低流动性: ${liquidity_result['usd_value']:,.0f} < $100k"
            )
        
        # 4. 持仓集中度
        concentration_result = await self._check_concentration(symbol)
        checks['concentration'] = concentration_result
        
        if concentration_result['top10_pct'] > 50:
            warnings.append(
                f"⚠️ 高度集中: Top 10持有 {concentration_result['top10_pct']:.1f}%"
            )
        
        # 5. 计算综合评分
        risk_score = self._calculate_score(checks)
        rating = self._get_rating(risk_score)
        is_safe = risk_score >= self.min_safe_score and len(warnings) == 0
        
        return RiskReport(
            symbol=symbol,
            risk_score=risk_score,
            rating=rating,
            warnings=warnings,
            checks=checks,
            is_safe=is_safe
        )
    
    async def _check_honeypot(self, symbol: str) -> dict:
        """Honeypot检测 (使用免费API)"""
        try:
            # 提取合约地址 (假设你有mapping)
            contract_address = await self._get_contract_address(symbol)
            
            # 调用 honeypot.is API
            async with aiohttp.ClientSession() as session:
                url = f"https://api.honeypot.is/v2/IsHoneypot"
                params = {'address': contract_address}
                
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    
                    return {
                        'is_honeypot': data.get('honeypotResult', {}).get('isHoneypot', False),
                        'risk': 'critical' if data.get('honeypotResult', {}).get('isHoneypot') else 'safe'
                    }
        except Exception as e:
            logger.warning(f"Honeypot检测失败: {e}")
            return {'is_honeypot': False, 'risk': 'unknown'}
    
    async def _check_tax(self, symbol: str) -> dict:
        """税率检查"""
        # 可以从 DEX 路由器模拟交易获取
        # 或使用 tokensniffer.com API
        return {
            'buy_tax': 0,
            'sell_tax': 0,
            'risk': 'low'
        }
    
    async def _check_liquidity(self, symbol: str) -> dict:
        """流动性检查"""
        try:
            # 方法1: Binance API (你已经在用)
            from src.collectors.binance_realtime_collector import BinanceRealtimeCollector
            
            collector = BinanceRealtimeCollector()
            orderbook = await collector.get_orderbook(symbol, limit=100)
            
            # 计算买卖盘深度
            bid_depth = sum(float(bid[1]) * float(bid[0]) for bid in orderbook['bids'][:20])
            ask_depth = sum(float(ask[1]) * float(ask[0]) for ask in orderbook['asks'][:20])
            
            total_liquidity = bid_depth + ask_depth
            
            return {
                'usd_value': total_liquidity,
                'bid_depth': bid_depth,
                'ask_depth': ask_depth,
                'risk': 'low' if total_liquidity > 100000 else 'high'
            }
        except Exception as e:
            logger.warning(f"流动性检测失败: {e}")
            return {'usd_value': 0, 'risk': 'high'}
    
    async def _check_concentration(self, symbol: str) -> dict:
        """持仓集中度检查"""
        # 可以使用 Etherscan API 或 BSCScan API
        # 暂时返回默认值
        return {
            'top10_pct': 30,  # 假设Top 10持有30%
            'risk': 'medium'
        }
    
    def _calculate_score(self, checks: dict) -> float:
        """计算综合风险评分"""
        weights = {
            'honeypot': 50,      # Honeypot权重最高
            'tax': 15,
            'liquidity': 20,
            'concentration': 15
        }
        
        risk_values = {
            'safe': 100,
            'low': 75,
            'medium': 50,
            'high': 25,
            'critical': 0
        }
        
        total_score = 0
        total_weight = sum(weights.values())
        
        for check_name, weight in weights.items():
            if check_name in checks:
                risk_level = checks[check_name].get('risk', 'medium')
                score = risk_values.get(risk_level, 50)
                total_score += score * weight
        
        return total_score / total_weight
    
    def _get_rating(self, score: float) -> str:
        """评级"""
        if score >= 80: return 'A (Excellent)'
        elif score >= 60: return 'B (Good)'
        elif score >= 40: return 'C (Moderate)'
        elif score >= 20: return 'D (High Risk)'
        else: return 'F (Extreme Risk)'
    
    async def _get_contract_address(self, symbol: str) -> str:
        """获取合约地址 (需要维护一个mapping)"""
        # 简化实现，实际需要从链上查询
        mapping = {
            'BTC/USDT': '0x...',  # 示例
            'ETH/USDT': '0x...'
        }
        return mapping.get(symbol, '')
```

**集成到信号生成器**:
```python
# 修改 src/analyzers/trading_signal_generator.py

from src.risk.risk_checker import TokenRiskChecker

class TradingSignalGenerator:
    
    def __init__(self):
        # ... 现有代码 ...
        self.risk_checker = TokenRiskChecker()
    
    async def generate_signal(self, symbol: str, data: dict) -> Optional[dict]:
        """生成信号前先做风险检查"""
        
        # 原有信号生成逻辑
        signal = await self._generate_raw_signal(symbol, data)
        
        if not signal:
            return None
        
        # 🔒 风险检查
        risk_report = await self.risk_checker.check_token(symbol)
        
        if not risk_report.is_safe:
            logger.warning(
                f"⚠️ {symbol} 风险评分: {risk_report.risk_score}/100 "
                f"- 禁止交易\n"
                f"警告: {', '.join(risk_report.warnings)}"
            )
            return None
        
        # 添加风险信息到信号
        signal['risk_score'] = risk_report.risk_score
        signal['risk_warnings'] = risk_report.warnings
        
        return signal
```

---

#### **3. 订单管理面板** (Telegram命令扩展)

**来源**: OKX - `account.ts` + Gate - `gate-exchange-assets-manager`

**实现方案**:
```python
# crypto-monitor-bot/hermes_integration/telegram_commands.py (扩展)

class TelegramCommandHandler:
    
    async def cmd_positions(self, update, context):
        """
        /positions - 查看当前持仓
        
        显示:
        - 持仓列表
        - 盈亏情况
        - 持仓时长
        - 止损价格
        """
        positions = lana_engine.get_positions()
        
        if not positions:
            await update.message.reply_text("📭 当前无持仓")
            return
        
        msg = "📊 当前持仓\n\n"
        
        for symbol, pos in positions.items():
            current_price = await get_current_price(symbol)
            pnl = (current_price - pos.entry_price) * pos.size / pos.entry_price
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            
            holding_time = datetime.now() - pos.entry_time
            
            msg += f"🪙 {symbol}\n"
            msg += f"  进场: ${pos.entry_price:,.2f}\n"
            msg += f"  现价: ${current_price:,.2f}\n"
            msg += f"  盈亏: ${pnl:+.2f} ({pnl_pct:+.2f}%)\n"
            msg += f"  持仓: {holding_time.seconds//60}分钟\n"
            msg += f"  止损: ${pos.stop_loss_price:,.2f}\n"
            msg += f"  状态: {pos.status.value}\n\n"
        
        await update.message.reply_text(msg)
    
    async def cmd_close(self, update, context):
        """
        /close <symbol> - 手动平仓
        
        Example:
            /close BTC/USDT
        """
        if not context.args:
            await update.message.reply_text("用法: /close BTC/USDT")
            return
        
        symbol = context.args[0]
        
        # 执行平仓
        result = await lana_engine.close_position(symbol)
        
        if result:
            await update.message.reply_text(
                f"✅ {symbol} 平仓成功\n"
                f"盈亏: ${result.pnl:+.2f} ({result.pnl_pct:+.2f}%)"
            )
        else:
            await update.message.reply_text(f"❌ {symbol} 平仓失败")
    
    async def cmd_balance(self, update, context):
        """
        /balance - 查看账户余额
        """
        from src.trading.spot_executor import SpotTradeExecutor
        
        executor = SpotTradeExecutor()
        balance = await executor.get_balance('USDT')
        
        await update.message.reply_text(
            f"💰 账户余额\n\n"
            f"USDT: {balance:,.2f}\n"
            f"可用: {balance:,.2f}\n"
            f"冻结: 0.00"
        )
    
    async def cmd_stats(self, update, context):
        """
        /stats - 交易统计
        """
        stats = lana_engine.get_statistics()
        
        msg = f"""
📈 交易统计

总交易: {stats['total_trades']}
胜率: {stats['win_rate']:.1f}%
总盈亏: ${stats['total_pnl']:+,.2f}
平均持仓: {stats['avg_holding_time']}分钟
最大回撤: ${stats['max_drawdown']:,.2f}
今日盈亏: ${stats['today_pnl']:+,.2f}
"""
        
        await update.message.reply_text(msg)
```

---

### **P1 - 本月可选 (增强功能)** 🔶

#### **4. 技术指标计算库** (70+指标)

**来源**: OKX - `indicator.ts`

**为什么需要**: 增强你的V4A/V7/V8策略，添加更多技术指标确认。

**实现方案**:
```python
# crypto-monitor-bot/src/indicators/technical_indicators.py

import numpy as np
import pandas as pd
from typing import List, Tuple

class TechnicalIndicators:
    """技术指标计算库 (基于OKX的70+指标)"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """RSI 相对强弱指标"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[float, float, float]:
        """MACD 指标"""
        prices_series = pd.Series(prices)
        
        ema_fast = prices_series.ewm(span=fast).mean()
        ema_slow = prices_series.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return (
            macd_line.iloc[-1],
            signal_line.iloc[-1],
            histogram.iloc[-1]
        )
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """布林带"""
        prices_series = pd.Series(prices)
        
        sma = prices_series.rolling(period).mean()
        std = prices_series.rolling(period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return (
            upper_band.iloc[-1],
            sma.iloc[-1],
            lower_band.iloc[-1]
        )
    
    @staticmethod
    def calculate_atr(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> float:
        """ATR 平均真实波幅"""
        tr_list = []
        
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        atr = np.mean(tr_list[-period:])
        return atr
```

**集成到信号生成器**:
```python
# 增强 src/analyzers/trading_signal_generator.py

from src.indicators.technical_indicators import TechnicalIndicators

class TradingSignalGenerator:
    
    async def generate_enhanced_signal(self, symbol: str, data: dict) -> dict:
        """增强版信号生成 (添加技术指标确认)"""
        
        # 原有信号
        base_signal = await self.generate_signal(symbol, data)
        
        if not base_signal:
            return None
        
        # 获取历史价格
        prices = await self._get_price_history(symbol, limit=100)
        
        # 计算技术指标
        indicators = TechnicalIndicators()
        
        rsi = indicators.calculate_rsi(prices)
        macd, signal, hist = indicators.calculate_macd(prices)
        bb_upper, bb_mid, bb_lower = indicators.calculate_bollinger_bands(prices)
        
        # 技术指标确认
        tech_signals = []
        
        if rsi < 30:
            tech_signals.append('RSI_OVERSOLD')
        elif rsi > 70:
            tech_signals.append('RSI_OVERBOUGHT')
        
        if macd > signal and hist > 0:
            tech_signals.append('MACD_BULLISH')
        elif macd < signal and hist < 0:
            tech_signals.append('MACD_BEARISH')
        
        current_price = prices[-1]
        if current_price < bb_lower:
            tech_signals.append('BB_LOWER_TOUCH')
        elif current_price > bb_upper:
            tech_signals.append('BB_UPPER_TOUCH')
        
        # 增强信号评分
        if 'MACD_BULLISH' in tech_signals and base_signal['action'] == 'BUY':
            base_signal['score'] += 5
        
        base_signal['technical_signals'] = tech_signals
        base_signal['rsi'] = rsi
        base_signal['macd'] = {'macd': macd, 'signal': signal, 'hist': hist}
        
        return base_signal
```

---

#### **5. 网格交易策略** (自动化策略)

**来源**: OKX - `bot/grid.ts`

**实现方案**:
```python
# crypto-monitor-bot/src/strategies/grid_strategy.py

import numpy as np
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class GridConfig:
    """网格配置"""
    symbol: str
    price_range: Tuple[float, float]  # (下限, 上限)
    grid_count: int
    investment_usdt: float
    mode: str = 'arithmetic'  # 'arithmetic' | 'geometric'


class GridTradingStrategy:
    """网格交易策略 (适合震荡行情)"""
    
    def __init__(self, executor: SpotTradeExecutor):
        self.executor = executor
        self.active_grids: Dict[str, GridConfig] = {}
    
    async def create_grid(self, config: GridConfig) -> bool:
        """
        创建网格
        
        Example:
            config = GridConfig(
                symbol='BTC/USDT',
                price_range=(60000, 70000),
                grid_count=10,
                investment_usdt=1000
            )
            await grid_strategy.create_grid(config)
        """
        # 计算网格价格
        if config.mode == 'arithmetic':
            price_levels = np.linspace(
                config.price_range[0],
                config.price_range[1],
                config.grid_count
            )
        else:  # geometric
            price_levels = np.geomspace(
                config.price_range[0],
                config.price_range[1],
                config.grid_count
            )
        
        # 批量下限价单
        amount_per_grid = config.investment_usdt / config.grid_count
        
        for i, price in enumerate(price_levels):
            # 偶数网格买入，奇数网格卖出
            side = 'buy' if i % 2 == 0 else 'sell'
            amount = amount_per_grid / price
            
            try:
                order = await self.executor.place_limit_order(
                    symbol=config.symbol,
                    side=side,
                    price=price,
                    amount=amount
                )
                
                logger.info(f"✅ 网格{i}: {side} @{price}")
            except Exception as e:
                logger.error(f"❌ 网格{i}创建失败: {e}")
        
        self.active_grids[config.symbol] = config
        
        return True
    
    async def monitor_grid(self, symbol: str):
        """监控网格 (自动补单)"""
        # 检查已成交订单
        # 在对应价格补单
        # 实现网格自动运转
        pass
```

---

## 🎯 **实施计划**

### **Week 1: 核心交易执行**
```bash
# Day 1-2: 实现 SpotTradeExecutor
crypto-monitor-bot/
└── src/
    └── trading/
        └── spot_executor.py  ✅

# Day 3-4: 集成到 Lana 引擎
hermes_integration/
└── lana_trading_engine.py  (修改)

# Day 5-6: 测试网测试
- 连接Binance测试网
- 模拟交易流程
- 验证止损逻辑

# Day 7: 上线监控
- 小仓位真实测试 (100 USDT)
- 监控执行日志
- 调整参数
```

### **Week 2: 风险管理**
```bash
# Day 8-10: 实现风险检查器
src/
└── risk/
    └── risk_checker.py  ✅

# Day 11-12: 集成到信号生成器
src/analyzers/
└── trading_signal_generator.py  (修改)

# Day 13-14: Telegram命令扩展
hermes_integration/
└── telegram_commands.py  (扩展)
```

---

## 📝 **关键注意事项**

### **1. 安全第一**
```python
# ⚠️ 强制使用测试网先测试
executor = SpotTradeExecutor(
    testnet=True  # 必须先在测试网跑通
)

# ⚠️ 设置最大亏损限制
MAX_DAILY_LOSS = 500  # USDT
if daily_loss > MAX_DAILY_LOSS:
    logger.critical("🚨 达到每日亏损上限，停止交易!")
    await emergency_stop()
```

### **2. API密钥管理**
```bash
# 使用环境变量
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# 或使用配置文件 (加密存储)
~/.crypto-monitor-bot/secrets.yaml
```

### **3. 日志监控**
```python
# 所有交易操作必须记录
logger.info(f"[TRADE] {symbol} {side} {amount}@{price}")
logger.warning(f"[RISK] {symbol} score={risk_score}")
logger.error(f"[ERROR] Order failed: {error}")
```

### **4. 回测验证**
```python
# 用历史数据测试策略
from src.backtesting.backtest_engine import BacktestEngine

backtest = BacktestEngine()
result = await backtest.run(
    strategy='lana',
    start_date='2024-01-01',
    end_date='2024-04-01',
    initial_capital=10000
)

print(f"回测结果: {result.total_return:.2%}")
print(f"胜率: {result.win_rate:.2%}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

---

## ✅ **下一步行动**

1. **立即开始**: 创建 `spot_executor.py` (预计2小时)
2. **测试网验证**: 连接Binance测试网下单 (预计1天)
3. **集成Lana**: 修改 `lana_trading_engine.py` (预计4小时)
4. **小额真实测试**: 100 USDT测试 (预计1周监控)

**预计时间**: 2周完成核心功能

**风险等级**: ⚠️ 中等 (已有信号生成，新增自动执行)

**建议**: 从最小仓位(50-100 USDT)开始，逐步增加到1000 USDT标准仓位
