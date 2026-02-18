import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def main():
    async with streamablehttp_client(url="https://cocktail-mcp-ge-staging-lxo6yz2aha-uc.a.run.app/mcp/") as (rx, tx):
        async with ClientSession(rx, tx) as session:
            await session.initialize()
            print("Session initialized successfully")
            tools = await session.list_tools()
            print("Tools:", tools)

asyncio.run(main())
