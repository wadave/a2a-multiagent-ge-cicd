import asyncio
import os
import httpx
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from a2a_agents.common.adk_base_mcp_agent_executor import CocktailAgentExecutor

async def main():
    mcp_url = os.popen("gcloud run services describe cocktail-mcp-ge-staging --region us-central1 --project dw-genai-dev --format='value(status.url)'").read().strip() + "/mcp/"
    os.environ["CT_MCP_SERVER_URL"] = mcp_url
    
    executor = CocktailAgentExecutor()
    executor._init_agent()
    
    # Try to refresh auth and check the toolset headers
    executor._refresh_mcp_auth()
    
    toolset = executor.agent.tools[0]
    headers = toolset._connection_params.headers
    print(f"Headers configured: {headers.keys()}")
    
    # Send a dummy request to the configured URL to see if it allows unauthenticated
    async with httpx.AsyncClient() as client:
        resp = await client.get(mcp_url, headers=headers)
        print(f"Response status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response body: {resp.text}")

asyncio.run(main())
