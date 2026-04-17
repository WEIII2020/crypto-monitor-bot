"""
Dynamic Symbol Selector
Automatically selects coins most likely to be manipulated by whales
"""

import aiohttp
from typing import List, Dict, Optional
from datetime import datetime

from src.utils.logger import logger


class SymbolSelector:
    """Select symbols based on market cap, volume, and other criteria"""

    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"

        # Selection criteria
        self.min_volume_usd = 5_000_000      # $5M minimum daily volume
        self.max_volume_usd = 50_000_000     # $50M maximum (avoid too popular)
        self.min_price = 0.01                # Minimum price $0.01
        self.max_price = 10.0                # Maximum price $10

        # Tier definitions
        self.tier1_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

        # Excluded patterns (stablecoins, fiat, etc.)
        self.excluded_bases = [
            'USDT', 'USDC', 'BUSD', 'TUSD', 'USDP', 'DAI',  # Stablecoins
            'EUR', 'GBP', 'AUD', 'PAX',                      # Fiat
            'UP', 'DOWN', 'BULL', 'BEAR'                     # Leveraged tokens
        ]

    async def fetch_all_tickers(self) -> List[Dict]:
        """
        Fetch 24h ticker data for all symbols from Binance

        Returns:
            List of ticker data dicts
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.binance_api}/ticker/24hr"

                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch tickers: HTTP {response.status}")
                        return []

                    data = await response.json()
                    logger.info(f"Fetched {len(data)} tickers from Binance")
                    return data

        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return []

    def normalize_symbol(self, binance_symbol: str) -> str:
        """Convert BTCUSDT to BTC/USDT"""
        if binance_symbol.endswith('USDT'):
            base = binance_symbol[:-4]
            return f"{base}/USDT"
        return binance_symbol

    def is_valid_symbol(self, ticker: Dict) -> bool:
        """
        Check if a symbol meets basic criteria

        Args:
            ticker: 24h ticker data from Binance

        Returns:
            True if symbol is valid for monitoring
        """
        try:
            symbol = ticker['symbol']

            # Must be USDT pair
            if not symbol.endswith('USDT'):
                return False

            # Extract base currency
            base = symbol[:-4]

            # Exclude stablecoins and other unwanted tokens
            if base in self.excluded_bases:
                return False

            # Exclude leveraged tokens and weird symbols
            excluded_patterns = [
                'UP', 'DOWN', 'BULL', 'BEAR',  # Leveraged tokens
                'BROCCOLI', 'BANANA', 'BARD', 'FF', 'TREE',  # Weird meme tokens with db issues
            ]
            for excluded in excluded_patterns:
                if excluded in base:
                    return False

            # Exclude symbols with numbers (e.g., BROCCOLI714)
            if any(char.isdigit() for char in base):
                return False

            # Check price range
            price = float(ticker['lastPrice'])
            if price < self.min_price or price > self.max_price:
                return False

            # Check volume range
            volume_usd = float(ticker['quoteVolume'])
            if volume_usd < self.min_volume_usd or volume_usd > self.max_volume_usd:
                return False

            return True

        except (KeyError, ValueError) as e:
            logger.debug(f"Invalid ticker data: {e}")
            return False

    async def select_symbols(
        self,
        tier2_count: int = 20,
        tier3_count: int = 30,
        tier4_count: int = 0
    ) -> Dict[str, List[str]]:
        """
        Select symbols for monitoring across different tiers

        Args:
            tier2_count: Number of mid-cap coins (will be implemented later)
            tier3_count: Number of small-cap active coins
            tier4_count: Number of new hot coins (will be implemented later)

        Returns:
            Dict with tier names as keys and symbol lists as values
        """
        logger.info("Starting symbol selection...")

        # Fetch all tickers
        all_tickers = await self.fetch_all_tickers()
        if not all_tickers:
            logger.warning("No tickers fetched, using default symbols")
            return {'tier1': self.tier1_symbols}

        # Filter valid symbols
        valid_tickers = [t for t in all_tickers if self.is_valid_symbol(t)]
        logger.info(f"Found {len(valid_tickers)} valid symbols")

        # Sort by volume (descending)
        valid_tickers.sort(key=lambda x: float(x['quoteVolume']), reverse=True)

        # Select Tier 3: Top small-cap coins by volume
        tier3_symbols = []
        for ticker in valid_tickers[:tier3_count]:
            normalized = self.normalize_symbol(ticker['symbol'])
            tier3_symbols.append(normalized)
            logger.debug(
                f"Selected {normalized}: "
                f"Price=${float(ticker['lastPrice']):.4f}, "
                f"Volume=${float(ticker['quoteVolume']):,.0f}"
            )

        result = {
            'tier1': self.tier1_symbols,
            'tier3': tier3_symbols
        }

        total = len(result['tier1']) + len(result['tier3'])
        logger.info(
            f"Symbol selection complete: "
            f"Tier1={len(result['tier1'])}, "
            f"Tier3={len(result['tier3'])}, "
            f"Total={total}"
        )

        return result

    async def get_monitoring_list(self, max_symbols: int = 50) -> List[str]:
        """
        Get flat list of symbols for monitoring

        Args:
            max_symbols: Maximum number of symbols to monitor

        Returns:
            Flat list of symbols
        """
        # Calculate tier distribution
        tier1_count = len(self.tier1_symbols)
        remaining = max_symbols - tier1_count
        tier3_count = min(remaining, 45)  # Leave room for tier1

        # Select symbols
        tiers = await self.select_symbols(tier3_count=tier3_count)

        # Flatten to single list
        symbols = []
        symbols.extend(tiers['tier1'])
        symbols.extend(tiers.get('tier3', []))

        logger.info(f"Monitoring list ready: {len(symbols)} symbols")
        return symbols

    def format_summary(self, tiers: Dict[str, List[str]]) -> str:
        """Format a human-readable summary of selected symbols"""
        lines = []
        lines.append("=" * 60)
        lines.append("MONITORING SYMBOL SELECTION")
        lines.append("=" * 60)

        for tier_name, symbols in tiers.items():
            lines.append(f"\n{tier_name.upper()}: {len(symbols)} symbols")
            lines.append("-" * 40)

            # Show first 10 symbols
            for symbol in symbols[:10]:
                lines.append(f"  • {symbol}")

            if len(symbols) > 10:
                lines.append(f"  ... and {len(symbols) - 10} more")

        lines.append("=" * 60)
        return "\n".join(lines)


# Example usage
async def main():
    """Test the symbol selector"""
    selector = SymbolSelector()

    # Get monitoring list
    symbols = await selector.get_monitoring_list(max_symbols=50)

    print(f"\n✅ Selected {len(symbols)} symbols for monitoring:\n")
    for i, symbol in enumerate(symbols, 1):
        print(f"{i:2d}. {symbol}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
