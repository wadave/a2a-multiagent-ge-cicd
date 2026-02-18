import asyncio
import os
import logging
logging.basicConfig(level=logging.INFO)

from a2a_agents.cocktail_agent.cocktail_agent_executor import CocktailAgentExecutor
from google.adk.tools.mcp_tool import mcp_session_manager

async def main():
    mcp_url = os.popen("gcloud run services describe cocktail-mcp-ge-staging --region us-central1 --project dw-genai-dev --format='value(status.url)'").read().strip() + "/mcp/"
    os.environ["CT_MCP_SERVER_URL"] = mcp_url
    
    executor = CocktailAgentExecutor()
    executor._init_agent()
    executor._refresh_mcp_auth()
    
    toolset = executor.agent.tools[0]
    headers = toolset._connection_params.headers
    print(f"Headers: {headers.keys()}")

    try:
        session = await mcp_session_manager.create_session(toolset._connection_params)
        print("MCP Session created successfully")
        await session.close()
    except Exception as e:
        print(f"Failed to create session: {e}")

asyncio.run(main())
