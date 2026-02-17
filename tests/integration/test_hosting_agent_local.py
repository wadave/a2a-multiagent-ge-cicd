import asyncio
import logging
import os
import subprocess
import sys
from typing import Dict

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import the agent factory
from a2a_agents.hosting_agent.adk_agent import create_hosting_agent, MyClientFactory
import a2a_agents.hosting_agent.adk_agent as adk_agent_module

logging.basicConfig(level=logging.INFO)

# --- Monkeypatch Auth for Local Testing ---
# The adk_agent.py uses MyClientFactory which uses GoogleAuthRefresh (defined in adk_agent.py)
# We need to patch GoogleAuthRefresh or the default() call inside it.

def mock_get_gcloud_token() -> str:
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()
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
# Note: adk_agent.py imports default from google.auth
# We need to patch it where it is used.
# It is used inside GoogleAuthRefresh.__init__
adk_agent_module.default = mock_default
logging.info("Monkeypatched google.auth.default for local testing")

# --- Test Logic ---

async def test_hosting_agent_local():
    # Set remote agent URLs (deployed instances)
    os.environ["CT_AGENT_URL"] = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/8358349955399680000/a2a"
    os.environ["WEA_AGENT_URL"] = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/5302657608228798464/a2a"
    
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
    
    # Create session
    await runner.session_service.create_session(
        app_name=agent.name, user_id=user_id, session_id=session_id
    )

    # Test 1: Weather
    query = "What is the weather in San Francisco?"
    print(f"\nUser Query: {query}")
    
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    async for event in runner.run_async(
        session_id=session_id,
        user_id=user_id,
        new_message=content
    ):
        print(f"Event type: {type(event).__name__}, is_final: {event.is_final_response()}")
        if hasattr(event, 'content') and event.content:
            print(f"Content: {event.content}")
        if hasattr(event, 'error') and event.error:
            print(f"Error: {event.error}")

        if event.is_final_response():
            print("\n--- Final Response (Weather) ---")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)
            else:
                print("No content in final response")
                if hasattr(event, 'error') and event.error:
                    print(f"Error details: {event.error}")

    # Test 2: Cocktail
    query = "List a random cocktail"
    print(f"\nUser Query: {query}")
    
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    async for event in runner.run_async(
        session_id=session_id,
        user_id=user_id,
        new_message=content
    ):
        print(f"Event type: {type(event).__name__}, is_final: {event.is_final_response()}")
        if hasattr(event, 'content') and event.content:
            print(f"Content: {event.content}")
        if hasattr(event, 'error') and event.error:
            print(f"Error: {event.error}")

        if event.is_final_response():
            print("\n--- Final Response (Cocktail) ---")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)
            else:
                print("No content in final response")
                if hasattr(event, 'error') and event.error:
                    print(f"Error details: {event.error}")


if __name__ == "__main__":
    asyncio.run(test_hosting_agent_local())
