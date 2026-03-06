"""Local integration test for the Hosting Agent (runs agent in-process)."""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from test_config import CT_AGENT_URL, WEA_AGENT_URL

import a2a_agents.hosting_agent.adk_agent as adk_agent_module
from a2a_agents.hosting_agent.adk_agent import create_hosting_agent

logging.basicConfig(level=logging.INFO)


# --- Monkeypatch Auth for Local Testing ---


def mock_get_gcloud_token() -> str:
    try:
        return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    except Exception as e:
        logging.error(f"Failed to get gcloud token: {e}")
        return ""


class MockCredentials:
    def __init__(self, token):
        self.token = token
        self.valid = True

    def refresh(self, request):
        self.token = mock_get_gcloud_token()


def mock_default(scopes=None):
    token = mock_get_gcloud_token()
    return MockCredentials(token), "mock-project"


# Patch google.auth.default used in adk_agent.py
adk_agent_module.default = mock_default
logging.info("Monkeypatched google.auth.default for local testing")

# --- Test Logic ---


async def test_hosting_agent_local():
    # Load environment variables from .env file
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../src/a2a_agents/.env"))

    ct_url = os.environ.get("CT_AGENT_URL") or CT_AGENT_URL
    wea_url = os.environ.get("WEA_AGENT_URL") or WEA_AGENT_URL

    if not ct_url or not wea_url:
        print("ERROR: CT_AGENT_URL and WEA_AGENT_URL must be set (env vars or test_config).")
        sys.exit(1)

    os.environ["CT_AGENT_URL"] = ct_url
    os.environ["WEA_AGENT_URL"] = wea_url

    print(f"Using Cocktail Agent: {ct_url}")
    print(f"Using Weather Agent: {wea_url}")

    print("\n--- Creating Hosting Agent ---")
    agent = create_hosting_agent()
    print(f"Agent created: {agent.name}")
    print(f"Sub-agents: {[sa.name for sa in agent.sub_agents]}")

    print("\n--- Running Hosting Agent (Local) ---")

    runner = Runner(
        app_name=agent.name,
        agent=agent,
        session_service=InMemorySessionService(),
    )

    session_id = "test-session-local"
    user_id = "local-user"

    await runner.session_service.create_session(
        app_name=agent.name, user_id=user_id, session_id=session_id
    )

    # Test 1: Weather
    query = "What is the weather in San Francisco?"
    print(f"\nUser Query: {query}")

    content = types.Content(role="user", parts=[types.Part(text=query)])

    async for event in runner.run_async(
        session_id=session_id, user_id=user_id, new_message=content
    ):
        print(f"Event type: {type(event).__name__}, is_final: {event.is_final_response()}")
        if hasattr(event, "content") and event.content:
            print(f"Content: {event.content}")
        if hasattr(event, "error") and event.error:
            print(f"Error: {event.error}")

        if event.is_final_response():
            print("\n--- Final Response (Weather) ---")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)
            else:
                print("No content in final response")
                if hasattr(event, "error") and event.error:
                    print(f"Error details: {event.error}")

    # Test 2: Cocktail
    query = "List a random cocktail"
    print(f"\nUser Query: {query}")

    content = types.Content(role="user", parts=[types.Part(text=query)])

    async for event in runner.run_async(
        session_id=session_id, user_id=user_id, new_message=content
    ):
        print(f"Event type: {type(event).__name__}, is_final: {event.is_final_response()}")
        if hasattr(event, "content") and event.content:
            print(f"Content: {event.content}")
        if hasattr(event, "error") and event.error:
            print(f"Error: {event.error}")

        if event.is_final_response():
            print("\n--- Final Response (Cocktail) ---")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)
            else:
                print("No content in final response")
                if hasattr(event, "error") and event.error:
                    print(f"Error details: {event.error}")


if __name__ == "__main__":
    asyncio.run(test_hosting_agent_local())
