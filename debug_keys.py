import asyncio
import aiohttp
import json


async def main():
    session = aiohttp.ClientSession()
    async with session.ws_connect("http://localhost:8088/ws") as ws:
        msg0 = await ws.receive()  # HELLO
        msg1 = await ws.receive()  # STATE_UPDATE
        d = json.loads(msg1.data)
        print(
            f"Top-level keys in STATE_UPDATE payload: {list(d.keys())}", flush=True)
        if "learning" in d:
            print(f"learning: {d['learning']}", flush=True)
    await session.close()

if __name__ == "__main__":
    asyncio.run(main())
