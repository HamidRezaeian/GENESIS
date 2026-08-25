import asyncio
import aiohttp
import json

async def test():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect("ws://localhost:8088/ws") as ws:
            print("Connected to WebSocket successfully!")
            for _ in range(5):
                msg = await ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    print(f"Received tick {data.get('tick')}: energy={data.get('energy'):.1f}, pos={data.get('agentPos')}, dir={data.get('agentDir')}")
                    if "mcts" in data:
                        print("  mcts:", data["mcts"].keys())
                await asyncio.sleep(0.1)

asyncio.run(test())
