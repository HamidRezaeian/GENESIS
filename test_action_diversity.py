import asyncio
import aiohttp
import json


async def main():
    session = aiohttp.ClientSession()
    async with session.ws_connect("http://localhost:8088/ws") as ws:
        msg0 = await ws.receive()  # HELLO
        for i in range(10):
            msg = await ws.receive()
            d = json.loads(msg.data)
            ap = d.get("mcts", {}).get("action_probs", [])
            sa = d.get("mcts", {}).get("selected_action", -1)
            pos = d.get("agentPos", [])
            tick = d.get("tick", 0)
            print(
                f"Tick {tick}: probs={[round(p, 3) for p in ap]}  action={sa}  pos={pos}")
    await session.close()

asyncio.run(main())
