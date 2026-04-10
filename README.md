# Crypto Monitor Bot

24/7 Cryptocurrency price monitoring and alert system.

## Features

- Monitor all cryptocurrencies across Binance, OKX, Gate.io, Raydium
- Detect price volatility (10%+ in 5 min)
- Identify market maker phases (accumulation, shakeout, pump, distribution)
- Real-time Telegram notifications
- 6-month historical data retention

## Quick Start

1. Copy `.env.example` to `.env` and configure
2. Run `docker-compose up -d`
3. Check logs: `docker-compose logs -f`

## Requirements

- Docker & Docker Compose
- Telegram Bot Token (from @BotFather)
- VPS with 2 cores, 2-4GB RAM (optional for deployment)

## Documentation

See `docs/` for detailed documentation.
