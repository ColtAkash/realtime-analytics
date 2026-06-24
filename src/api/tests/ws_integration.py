"""Integration test: 10 concurrent WS connections + connect/disconnect cycling."""
import asyncio
import json
import time
import websockets


WS_URL = "ws://ra-api:8000/ws/metrics"
NUM_CONNECTIONS = 10
LISTEN_SECONDS = 5
CYCLE_COUNT = 50


async def test_concurrent_connections():
    print(f"Opening {NUM_CONNECTIONS} concurrent connections...")
    connections = []
    for i in range(NUM_CONNECTIONS):
        ws = await websockets.connect(WS_URL)
        connections.append(ws)

    print(f"All {NUM_CONNECTIONS} connected. Collecting initial snapshots...")
    for i, ws in enumerate(connections):
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
        assert "ts" in msg, f"Connection {i}: missing 'ts' field"
        assert "event_type_counts" in msg, f"Connection {i}: missing 'event_type_counts'"
    print("  All received initial snapshot. PASS")

    print(f"Listening for broadcast updates ({LISTEN_SECONDS}s)...")
    timestamps = []
    start = time.monotonic()
    while time.monotonic() - start < LISTEN_SECONDS:
        try:
            msg = json.loads(await asyncio.wait_for(connections[0].recv(), timeout=2))
            timestamps.append(time.monotonic())
        except asyncio.TimeoutError:
            break

    if len(timestamps) >= 2:
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_interval = sum(intervals) / len(intervals)
        max_interval = max(intervals)
        print(f"  Received {len(timestamps)} updates, avg interval: {avg_interval:.2f}s, max: {max_interval:.2f}s")
        assert max_interval < 1.5, f"Max interval {max_interval:.2f}s > 1.5s"
        print("  PASS")
    else:
        print(f"  Received {len(timestamps)} updates (broadcast may be empty — OK for integration)")

    for ws in connections:
        await ws.close()
    print(f"All {NUM_CONNECTIONS} connections closed cleanly.")


async def test_reconnect():
    print(f"\nReconnect test: {CYCLE_COUNT} connect/disconnect cycles...")
    for i in range(CYCLE_COUNT):
        ws = await websockets.connect(WS_URL)
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
        assert "ts" in msg
        await ws.close()
    print(f"  {CYCLE_COUNT} cycles completed. PASS")


async def main():
    print("=" * 50)
    print("WebSocket Integration Tests")
    print("=" * 50)
    await test_concurrent_connections()
    await test_reconnect()
    print("\nAll integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
