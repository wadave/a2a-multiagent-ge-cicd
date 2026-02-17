import asyncio
import os
import httpx
import google.auth.transport.requests
from google.oauth2 import id_token
from fastmcp import Client
import subprocess

# MCP Server URLs
COCKTAIL_SERVER_URL = "https://cocktail-mcp-staging-lxo6yz2aha-uc.a.run.app"
WEATHER_SERVER_URL = "https://weather-mcp-staging-lxo6yz2aha-uc.a.run.app"

class BearerAuth(httpx.Auth):
    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request

def get_id_token(url):
    """Generates an ID token for the given URL."""
    # Try fetching via gcloud first (reliable for local user credentials)
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], text=True
        ).strip()
        if token:
            return token
    except Exception:
        pass

    # Fallback to google-auth (handles Service Accounts / GCE Metadata)
    auth_req = google.auth.transport.requests.Request()
    return id_token.fetch_id_token(auth_req, url)

async def test_cocktail_server():
    """Tests the Cocktail MCP server."""
    print("\n--- Testing Cocktail MCP Server ---")
    try:
        token = get_id_token(COCKTAIL_SERVER_URL)
        auth = BearerAuth(token)
    except Exception as e:
        print(f"Warning: Could not get ID token: {e}")
        auth = None

    # Note: Using /mcp endpoint for streamable-http transport
    async with Client(f"{COCKTAIL_SERVER_URL}/mcp/", auth=auth) as client:
        # List available tools
        tools = await client.list_tools()
        for tool in tools:
            print(f">>> 🛠️  Tool found: {tool.name}")
        
        # Call search tool
        print("Calling search_cocktail_by_name('margarita')...")
        result = await client.call_tool(
            "search_cocktail_by_name", {"name": "margarita"}
        )
        print(f"<<< ✅ Result: {result.content[0].text[:200]}...")

async def test_weather_server():
    """Tests the Weather MCP server."""
    print("\n--- Testing Weather MCP Server ---")
    try:
        token = get_id_token(WEATHER_SERVER_URL)
        auth = BearerAuth(token)
    except Exception as e:
        print(f"Warning: Could not get ID token: {e}")
        auth = None

    async with Client(f"{WEATHER_SERVER_URL}/mcp/", auth=auth) as client:
        # List available tools
        tools = await client.list_tools()
        for tool in tools:
            print(f">>> 🛠️  Tool found: {tool.name}")
        
        # Call forecast tool
        print("Calling get_forecast_by_city('New York', 'NY')...")
        result = await client.call_tool(
            "get_forecast_by_city", {"city": "New York", "state": "NY"}
        )
        print(f"<<< ✅ Result: {result.content[0].text[:200]}...")

async def main():
    try:
        await test_cocktail_server()
        await test_weather_server()
    except Exception as e:
        print(f"Error during testing: {e}")
        print("Ensure you have authenticated with 'gcloud auth application-default login'")
        print("and that the servers are reachable and configured with correct IAM permissions.")

if __name__ == "__main__":
    asyncio.run(main())
