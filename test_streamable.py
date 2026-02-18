import asyncio
import os
import httpx
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager, StreamableHTTPConnectionParams
from mcp import ClientSession

async def main():
    mcp_url = os.popen("gcloud run services describe cocktail-mcp-ge-staging --region us-central1 --project dw-genai-dev --format='value(status.url)'").read().strip() + "/mcp/"
    
    # Let's get a fresh token using gcloud since we're testing locally
    token = os.popen("gcloud auth print-identity-token").read().strip()
    headers = {"Authorization": f"Bearer {token}"}
    
    params = StreamableHTTPConnectionParams(
        url=mcp_url,
        headers=headers,
        timeout=10.0,
        sse_read_timeout=60.0
    )
    
    manager = MCPSessionManager(params)
    try:
        session = await manager.create_session()
        print("Successfully created session")
        await manager.close()
    except Exception as e:
        print(f"Exception creating session: {e}")

asyncio.run(main())
