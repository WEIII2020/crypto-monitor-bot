#!/usr/bin/env python3
"""Debug script to test Binance WebSocket connection"""

import asyncio
import json
import websockets

async def test_binance_ws():
    """Test Binance WebSocket and print received messages"""
    uri = "wss://stream.binance.com:9443/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Subscribe to BTC ticker
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": ["btcusdt@ticker"],
                "id": 1
            }

            await websocket.send(json.dumps(subscribe_msg))
            print(f"📤 Sent subscription: {subscribe_msg}")

            # Listen for messages
            print("\n🎧 Listening for messages (10 seconds)...")
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"\n📨 Message {i+1}:")
                    print(f"  Type: {data.get('e', 'N/A')}")
                    print(f"  Keys: {list(data.keys())}")
                    if 's' in data:
                        print(f"  Symbol: {data['s']}")
                    if 'c' in data:
                        print(f"  Price: {data['c']}")
                except asyncio.TimeoutError:
                    print(f"  ⏱️  Timeout waiting for message {i+1}")
                except Exception as e:
                    print(f"  ❌ Error: {e}")

            print("\n✅ Test complete")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_binance_ws())
