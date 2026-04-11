#!/bin/bash

# Crypto Monitor Bot - Quick Start Script

set -e

echo "🚀 Starting Crypto Monitor Bot..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please copy .env.example to .env and configure it:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import telegram" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Start Docker services
echo "🐳 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 5

# Check if database is initialized
if ! python3 -c "from src.database.postgres import postgres_client; import asyncio; asyncio.run(postgres_client.connect())" &> /dev/null 2>&1; then
    echo "🗄️  Initializing database..."
    python3 scripts/setup_db.py
fi

echo ""
echo "✅ All systems ready!"
echo ""
echo "🤖 Starting monitoring bot..."
echo "📱 You will receive alerts on Telegram"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the bot
python3 main.py
