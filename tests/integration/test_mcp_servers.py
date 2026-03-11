"""Integration test for deployed MCP servers with authentication."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import google.auth.transport.requests
import httpx
import pytest
from fastmcp import Client
from google.oauth2 import id_token

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from test_config import CT_MCP_BASE_URL, CT_MCP_SERVER_URL, WEA_MCP_BASE_URL, WEA_MCP_SERVER_URL


class BearerAuth(httpx.Auth):
    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


def get_id_token(url):
    """Generates an ID token for the given URL."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], text=True
        ).strip()
        if token:
            return token
    except Exception:
        pass

    auth_req = google.auth.transport.requests.Request()
    return id_token.fetch_id_token(auth_req, url)


async def test_cocktail_server():
    """Tests the Cocktail MCP server."""
    cocktail_base = os.environ.get("COCKTAIL_MCP_BASE_URL") or CT_MCP_BASE_URL
    cocktail_mcp = os.environ.get("CT_MCP_SERVER_URL") or CT_MCP_SERVER_URL

    if not cocktail_base or not cocktail_mcp:
        pytest.skip("Cocktail MCP server URL not configured.")

    print("\n--- Testing Cocktail MCP Server ---")
    print(f"Base URL: {cocktail_base}")
    print(f"MCP URL: {cocktail_mcp}")
    try:
        token = get_id_token(cocktail_base)
        auth = BearerAuth(token)
    except Exception as e:
        print(f"Warning: Could not get ID token: {e}")
        auth = None

    async with Client(cocktail_mcp, auth=auth) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "search_cocktail_by_name" in tool_names, (
            f"search_cocktail_by_name not found in tools: {tool_names}"
        )
        for tool in tools:
            print(f"  Tool found: {tool.name}")

        print("Calling search_cocktail_by_name('margarita')...")
        result = await client.call_tool("search_cocktail_by_name", {"name": "margarita"})
        assert result.content, "search_cocktail_by_name returned empty content"
        assert result.content[0].text, "search_cocktail_by_name returned empty text"
        assert "margarita" in result.content[0].text.lower(), (
            "Expected 'margarita' in response text"
        )
        print(f"  Result: {result.content[0].text[:200]}...")


async def test_weather_server():
    """Tests the Weather MCP server."""
    weather_base = os.environ.get("WEATHER_MCP_BASE_URL") or WEA_MCP_BASE_URL
    weather_mcp = os.environ.get("WEA_MCP_SERVER_URL") or WEA_MCP_SERVER_URL

    if not weather_base or not weather_mcp:
        pytest.skip("Weather MCP server URL not configured.")

    print("\n--- Testing Weather MCP Server ---")
    print(f"Base URL: {weather_base}")
    print(f"MCP URL: {weather_mcp}")
    try:
        token = get_id_token(weather_base)
        auth = BearerAuth(token)
    except Exception as e:
        print(f"Warning: Could not get ID token: {e}")
        auth = None

    async with Client(weather_mcp, auth=auth) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "get_forecast_by_city" in tool_names, (
            f"get_forecast_by_city not found in tools: {tool_names}"
        )
        for tool in tools:
            print(f"  Tool found: {tool.name}")

        print("Calling get_forecast_by_city('New York', 'NY')...")
        result = await client.call_tool("get_forecast_by_city", {"city": "New York", "state": "NY"})
        assert result.content, "get_forecast_by_city returned empty content"
        assert result.content[0].text, "get_forecast_by_city returned empty text"
        print(f"  Result: {result.content[0].text[:200]}...")


async def main():
    try:
        cocktail_base = os.environ.get("COCKTAIL_MCP_BASE_URL") or CT_MCP_BASE_URL
        cocktail_mcp = os.environ.get("CT_MCP_SERVER_URL") or CT_MCP_SERVER_URL
        if cocktail_base and cocktail_mcp:
            await test_cocktail_server()
        else:
            print("SKIP: Cocktail MCP server URL not configured.")

        weather_base = os.environ.get("WEATHER_MCP_BASE_URL") or WEA_MCP_BASE_URL
        weather_mcp = os.environ.get("WEA_MCP_SERVER_URL") or WEA_MCP_SERVER_URL
        if weather_base and weather_mcp:
            await test_weather_server()
        else:
            print("SKIP: Weather MCP server URL not configured.")
    except Exception as e:
        print(f"Error during testing: {e}")
        print("Ensure you have authenticated with 'gcloud auth application-default login'")
        print("and that the servers are reachable and configured with correct IAM permissions.")


if __name__ == "__main__":
    asyncio.run(main())
