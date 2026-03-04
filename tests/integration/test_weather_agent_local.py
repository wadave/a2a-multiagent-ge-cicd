"""Local integration test for the Weather Agent (runs agent in-process via A2aAgent)."""
import asyncio
import json
import logging
import os
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from starlette.requests import Request
from test_config import WEA_MCP_SERVER_URL
from vertexai.preview.reasoning_engines import A2aAgent

import a2a_agents.common.adk_base_mcp_agent_executor as executor_module
from a2a_agents.weather_agent.weather_agent_card import weather_agent_card
from a2a_agents.weather_agent.weather_agent_executor import WeatherAgentExecutor

logging.basicConfig(level=logging.INFO)

# --- Monkeypatch for Local Auth ---

def mock_get_gcp_auth_headers(audience: str) -> dict[str, str]:
    """Mock that uses gcloud to get a token working for local user."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], text=True
        ).strip()
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        logging.error(f"Failed to get gcloud token: {e}")
        return {}

# Apply the patch
executor_module.get_gcp_auth_headers = mock_get_gcp_auth_headers
logging.info("Monkeypatched get_gcp_auth_headers for local testing")

# --- Helpers ---

def receive_wrapper(data: dict) -> Callable[[], Awaitable[dict]]:
    async def receive():
        byte_data = json.dumps(data).encode("utf-8")
        return {"type": "http.request", "body": byte_data, "more_body": False}
    return receive

def build_post_request(data: dict[str, Any] | None = None) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "headers": [(b"content-type", b"application/json")],
        "app": None,
    }
    receiver = receive_wrapper(data)
    return Request(scope, receiver)

def build_get_request(path_params: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "query_string": b"",
        "app": None,
    }
    if path_params:
        scope["path_params"] = path_params
    async def receive():
        return {"type": "http.disconnect"}
    return Request(scope, receive)

# --- Test Logic ---

async def test_agent_locally():
    mcp_url = os.environ.get("WEA_MCP_SERVER_URL") or WEA_MCP_SERVER_URL

    if not mcp_url:
        print("ERROR: WEA_MCP_SERVER_URL must be set (env var or test_config).")
        sys.exit(1)

    os.environ["WEA_MCP_SERVER_URL"] = mcp_url

    print("\n--- Initializing A2aAgent (Weather) ---")
    print(f"MCP URL: {mcp_url}")
    a2a_agent = A2aAgent(
        agent_card=weather_agent_card, agent_executor_builder=WeatherAgentExecutor
    )
    a2a_agent.set_up()

    print("\n--- Getting Agent Card ---")
    request = build_get_request(None)
    response = await a2a_agent.handle_authenticated_agent_card(
        request=request, context=None
    )
    print(f"Agent Name: {response.get('name')}")

    print("\n--- Sending Message ---")
    message_data = {
        "message": {
            "messageId": f"msg-{os.urandom(8).hex()}",
            "content": [{"text": "weather in San Francisco?"}],
            "role": "ROLE_USER",
        },
    }
    request = build_post_request(message_data)
    response = await a2a_agent.on_message_send(request=request, context=None)

    task_id = response["task"]["id"]
    print(f"Task ID: {task_id}")

    print("\n--- Polling for Result ---")
    task_data = {"id": task_id}

    for _ in range(15):
        request = build_get_request(task_data)
        response = await a2a_agent.on_get_task(request=request, context=None)
        state = response.get("status", {}).get("state")
        print(f"Task State: {state}")

        if state == "TASK_STATE_COMPLETED":
            for artifact in response.get("artifacts", []):
                if artifact["parts"] and "text" in artifact["parts"][0]:
                    print(f"\nAnswer:\n{artifact['parts'][0]['text']}")
            break
        elif state == "TASK_STATE_FAILED":
            print(f"Task Failed: {response}")
            break

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_agent_locally())
