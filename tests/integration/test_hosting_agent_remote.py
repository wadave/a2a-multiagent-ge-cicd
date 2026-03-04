"""Remote integration test for the deployed Hosting Agent via A2A protocol."""
import asyncio
import logging
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

import httpx
from test_config import (
    DEFAULT_POLL_ATTEMPTS,
    DEFAULT_TIMEOUT,
    HOSTING_AGENT_URL,
    POLL_INTERVAL,
)
from test_utils import get_gcloud_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_message_and_wait(
    base_url: str,
    query: str,
    headers: dict,
    timeout: float = DEFAULT_TIMEOUT,
    poll_attempts: int = DEFAULT_POLL_ATTEMPTS,
    poll_interval: int = POLL_INTERVAL,
) -> tuple[bool, str]:
    """Send a message to the agent and wait for the response."""
    import os

    async with httpx.AsyncClient(timeout=timeout) as http_client:
        msg_url = f"{base_url}/v1/message:send"
        message_data = {
            "message": {
                "messageId": f"msg-{os.urandom(8).hex()}",
                "role": "1",
                "content": [{"text": query}],
            },
        }

        resp = await http_client.post(msg_url, headers=headers, json=message_data)
        if resp.status_code != 200:
            return False, f"Failed to send message: {resp.status_code} {resp.text}"

        task_resp = resp.json()
        task_id = task_resp.get("task", {}).get("id")
        if not task_id:
            return False, f"No task ID in response: {task_resp}"

        task_url = f"{base_url}/v1/tasks/{task_id}"
        for _ in range(poll_attempts):
            resp = await http_client.get(task_url, headers=headers)
            if resp.status_code != 200:
                return False, f"Failed to get task: {resp.status_code} {resp.text}"

            task_data = resp.json()
            state = task_data.get("status", {}).get("state")

            if state == "TASK_STATE_COMPLETED":
                artifacts = task_data.get("artifacts", [])
                response_text = ""
                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if "text" in part:
                            response_text += part["text"] + "\n"
                return True, response_text.strip()
            elif state == "TASK_STATE_FAILED":
                return False, f"Task failed: {task_data}"

            await asyncio.sleep(poll_interval)

        return False, "Timeout waiting for response"


async def test_agent(agent_url: str, agent_name: str, test_cases: list):
    """Test a deployed agent with multiple test cases."""
    print(f"\n{'='*80}")
    print(f"Testing: {agent_name}")
    print(f"URL: {agent_url}")
    print('='*80)

    token = get_gcloud_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Get agent card
    print("\n--- Getting Agent Card ---")
    async with httpx.AsyncClient() as http_client:
        card_url = f"{agent_url}/v1/card"
        try:
            resp = await http_client.get(card_url, headers=headers)
            if resp.status_code == 200:
                card = resp.json()
                print(f"Agent: {card.get('name')}")
                print(f"  Description: {card.get('description', 'N/A')[:100]}")
            else:
                print(f"Failed to get card: {resp.status_code}")
        except Exception as e:
            print(f"Error getting card: {e}")

    results = []
    for query, category in test_cases:
        print(f"\n--- Test: {category} ---")
        print(f"Query: {query}")

        try:
            success, response = await send_message_and_wait(agent_url, query, headers)

            if success:
                print("Response received:")
                print(response[:300] + ("..." if len(response) > 300 else ""))
                results.append((category, True, None))
            else:
                print(f"Error: {response}")
                results.append((category, False, response))

        except Exception as e:
            print(f"Exception: {e}")
            results.append((category, False, str(e)))

        await asyncio.sleep(1)

    # Summary
    print(f"\n{'='*80}")
    print(f"Test Summary for {agent_name}")
    print('='*80)
    for category, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"{status} {category}" + (f" - {error[:100]}" if error else ""))

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    print(f"\nPassed: {success_count}/{total_count}")

    return success_count == total_count


async def main():
    """Test the deployed hosting agent via A2A protocol."""
    if not HOSTING_AGENT_URL:
        print("ERROR: HOSTING_AGENT_URL not configured. Set HOSTING_AGENT_ID and PROJECT_NUMBER env vars.")
        sys.exit(1)

    test_cases = [
        ("Hello! How are you?", "greeting"),
        ("What is the weather in San Francisco, CA?", "weather"),
        ("Tell me about a Margarita cocktail", "cocktail"),
        ("What's in a Mojito?", "cocktail"),
    ]

    passed = await test_agent(HOSTING_AGENT_URL, "Hosting Agent (A2A)", test_cases)

    print(f"\n{'='*80}")
    print("OVERALL RESULT")
    print('='*80)
    if passed:
        print("All tests passed")
    else:
        print("Some tests failed")

    return passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
