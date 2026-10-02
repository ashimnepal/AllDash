"""Quick standalone script to test the Mac mini websocket feed.

Usage:
    python test_websocket.py
    python test_websocket.py ws://192.168.1.93:5555
"""
import asyncio
import json
import sys

import websockets

DEFAULT_URL = "ws://192.168.1.93:5555"


async def listen(url: str) -> None:
    print(f"Connecting to {url} ...")
    async with websockets.connect(url, open_timeout=10) as ws:
        print("Connected. Waiting for messages (Ctrl+C to stop)...\n")
        async for raw_message in ws:
            print("--- raw message ---")
            print(raw_message)
            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                print("(not valid JSON)")
                continue
            print("--- parsed JSON ---")
            print(json.dumps(data, indent=2))
            print()


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    try:
        asyncio.run(listen(url))
    except KeyboardInterrupt:
        print("\nStopped.")
    except (OSError, websockets.exceptions.WebSocketException) as exc:
        print(f"Connection failed: {exc}")


if __name__ == "__main__":
    main()
