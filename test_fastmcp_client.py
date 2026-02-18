import asyncio
import os
from fastmcp import Client

async def test_server():
    token = os.popen("gcloud auth print-identity-token").read().strip()
    headers = {"Authorization": f"Bearer {token}"}
    async with Client("https://cocktail-mcp-ge-staging-lxo6yz2aha-uc.a.run.app/mcp", headers=headers) as client:
        tools = await client.list_tools()
        for tool in tools:
            print(f">>> 🛠️  Tool found: {tool.name}")
        result = await client.call_tool("search_cocktail_by_name", {"name": "margarita"})
        print(f"<<< ✅ Result: {result[0].text}")

asyncio.run(test_server())
