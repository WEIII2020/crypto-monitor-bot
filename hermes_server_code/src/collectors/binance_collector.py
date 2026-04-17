import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import websockets

from src.collectors.base_collector import BaseCollector
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.utils.logger import logger
from src.utils.performance_monitor import performance_monitor


class BinanceCollector(BaseCollector):
    """Binance WebSocket collector for real-time price data"""

    def __init__(self):
        super().__init__('binance')
        self.ws_url = 'wss://stream.binance.com:9443/ws'
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.subscribe_id = 1

    async def connect(self):
        """Connect to Binance WebSocket"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.connected = True
            logger.info(f"Connected to Binance WebSocket at {self.ws_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("Disconnected from Binance WebSocket")

    def normalize_symbol(self, symbol: str) -> str:
        """
        Convert BTCUSDT to BTC/USDT format

        Strategy:
        - Common quote currencies: USDT, USDC, BTC, ETH, BNB, BUSD
        - Check from longest to shortest to avoid false matches
        """
        quote_currencies = ['USDT', 'USDC', 'BUSD', 'BTC', 'ETH', 'BNB']

        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"

        # Fallback: if no quote currency matched, return as-is
        return symbol

    def denormalize_symbol(self, symbol: str) -> str:
        """
        Convert BTC/USDT to btcusdt format for Binance API
        """
        return symbol.replace('/', '').lower()

    def get_subscribe_message(self, symbols: List[str]) -> Dict:
        """
        Create subscription message for Binance WebSocket

        Args:
            symbols: List of symbols in BTC/USDT format

        Returns:
            Subscription message dict
        """
        # Convert symbols to Binance format (btcusdt@ticker)
        params = [f"{self.denormalize_symbol(symbol)}@ticker" for symbol in symbols]

        return {
            'method': 'SUBSCRIBE',
            'params': params,
            'id': self.subscribe_id
        }

    async def subscribe_symbols(self, symbols: List[str]):
        """Subscribe to ticker updates for symbols"""
        if not self.connected or not self.ws:
            raise ConnectionError("WebSocket not connected")

        message = self.get_subscribe_message(symbols)
        await self.ws.send(json.dumps(message))
        self.subscribed_symbols = symbols

        logger.info(f"Subscribed to {len(symbols)} symbols on Binance")

    async def handle_message(self, message: Dict):
        """
        Process incoming ticker message from Binance

        Binance 24hrTicker message format:
        {
            "e": "24hrTicker",
            "E": 1672515782136,
            "s": "BTCUSDT",
            "p": "1234.56",
            "P": "2.30",
            "w": "40000.00",
            "x": "38765.43",
            "c": "40000.00",
            "Q": "0.123",
            "b": "39999.00",
            "B": "1.234",
            "a": "40001.00",
            "A": "2.345",
            "o": "38765.43",
            "h": "41000.00",
            "l": "38000.00",
            "v": "123456.78",
            "q": "4876543210.12",
            "O": 1672429382136,
            "C": 1672515782136,
            "F": 100000000,
            "L": 100001000,
            "n": 1001
        }
        """
        try:
            # Skip subscription confirmation messages
            if 'result' in message or 'id' in message:
                return

            # Only process 24hrTicker events
            if message.get('e') != '24hrTicker':
                return

            # Extract data
            symbol = self.normalize_symbol(message['s'])
            price = float(message['c'])
            volume = float(message['v'])
            timestamp = float(message['E']) / 1000  # Convert to seconds

            # Prepare price data
            price_data = {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'timestamp': timestamp,
                'exchange': self.exchange,
                'high': float(message['h']),
                'low': float(message['l']),
                'open': float(message['o']),
            }

            # Store in Redis (real-time cache)
            if redis_client.redis:
                try:
                    await redis_client.store_price(
                        self.exchange,
                        symbol,
                        timestamp,
                        price_data
                    )
                    performance_monitor.record_redis_write(success=True)
                except Exception as e:
                    performance_monitor.record_redis_write(success=False)
                    logger.error(f"Redis write failed for {symbol}: {e}")

            # Store in PostgreSQL (historical data) - with fallback
            if postgres_client:
                try:
                    # Get or create symbol
                    symbol_record = await postgres_client.get_symbol(symbol, self.exchange)
                    if not symbol_record:
                        # Parse base/quote currencies
                        parts = symbol.split('/')
                        base = parts[0] if len(parts) > 0 else symbol
                        quote = parts[1] if len(parts) > 1 else 'USDT'

                        symbol_id = await postgres_client.insert_symbol({
                            'symbol': symbol,
                            'exchange': self.exchange,
                            'base_currency': base,
                            'quote_currency': quote,
                            'is_active': True
                        })
                    else:
                        symbol_id = symbol_record['id']

                    # Insert price data
                    await postgres_client.insert_price_data({
                        'symbol_id': symbol_id,
                        'exchange': self.exchange,
                        'timestamp': datetime.fromtimestamp(timestamp),
                        'open': float(message['o']),
                        'high': float(message['h']),
                        'low': float(message['l']),
                        'close': float(message['c']),
                        'volume': volume
                    })
                    performance_monitor.record_postgres_write(success=True)
                except Exception as db_error:
                    # PostgreSQL write failed - log but continue
                    # Redis cache is already updated, so detection still works
                    performance_monitor.record_postgres_write(success=False)
                    logger.warning(f"PostgreSQL write failed for {symbol} (Redis OK): {db_error}")

            # Record message processing
            performance_monitor.record_message(symbol)
            logger.debug(f"Processed {symbol}: ${price:.2f}, Volume: {volume:.2f}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def start_listening(self):
        """
        Main message loop with auto-reconnection

        This method runs continuously, processing messages from the WebSocket.
        If connection drops, it will attempt to reconnect.
        """
        while True:
            try:
                # Connect with retry
                success = await self.connect_with_retry()
                if not success:
                    logger.error("Failed to establish connection, retrying in 60s")
                    await asyncio.sleep(60)
                    continue

                # Subscribe to symbols
                if self.subscribed_symbols:
                    await self.subscribe_symbols(self.subscribed_symbols)

                # Process messages
                while self.connected and self.ws:
                    try:
                        message_str = await asyncio.wait_for(
                            self.ws.recv(),
                            timeout=30.0
                        )
                        message = json.loads(message_str)
                        await self.handle_message(message)

                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        if self.ws:
                            await self.ws.ping()
                        continue

                    except websockets.ConnectionClosed:
                        logger.warning("WebSocket connection closed")
                        self.connected = False
                        break

            except Exception as e:
                logger.error(f"Error in listening loop: {e}", exc_info=True)
                self.connected = False

            # Wait before reconnecting
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
