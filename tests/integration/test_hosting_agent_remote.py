"""Remote integration test for the deployed Hosting Agent."""
import asyncio
import logging
import os
import sys
import httpx
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gcloud_token() -> str:
    """Get gcloud access token."""
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()
    except Exception as e:
        logger.error(f"Failed to get gcloud token: {e}")
        raise


async def send_message_and_wait(base_url: str, query: str, headers: dict, timeout: int = 60) -> tuple[bool, str]:
    """Send a message to the agent and wait for the response."""
    async with httpx.AsyncClient(timeout=timeout) as http_client:
        # Send message
        msg_url = f"{base_url}/v1/message:send"
        message_data = {
            "message": {
                "messageId": f"msg-{os.urandom(8).hex()}",
                "role": "1",  # User
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

        # Poll for result
        task_url = f"{base_url}/v1/tasks/{task_id}"
        for _ in range(30):  # Poll for up to 60 seconds
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

            await asyncio.sleep(2)

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
                print(f"✓ Agent: {card.get('name')}")
                print(f"  Description: {card.get('description', 'N/A')[:100]}")
            else:
                print(f"⚠️  Failed to get card: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  Error getting card: {e}")

    # Test each case
    results = []
    for query, category in test_cases:
        print(f"\n--- Test: {category} ---")
        print(f"Query: {query}")

        try:
            success, response = await send_message_and_wait(agent_url, query, headers)

            if success:
                print("✓ Response received:")
                print(response[:300] + ("..." if len(response) > 300 else ""))
                results.append((category, True, None))
            else:
                print(f"✗ Error: {response}")
                results.append((category, False, response))

        except Exception as e:
            print(f"✗ Exception: {e}")
            results.append((category, False, str(e)))

        await asyncio.sleep(1)  # Brief pause between tests

    # Summary
    print(f"\n{'='*80}")
    print(f"Test Summary for {agent_name}")
    print('='*80)
    for category, success, error in results:
        status = "✓" if success else "✗"
        print(f"{status} {category}" + (f" - {error[:100]}" if error else ""))

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    print(f"\nPassed: {success_count}/{total_count}")

    return success_count == total_count


async def main():
    """Test all deployed hosting agents."""
    # Test cases
    test_cases = [
        ("Hello! How are you?", "greeting"),
        ("What is the weather in San Francisco, CA?", "weather"),
        ("Tell me about a Margarita cocktail", "cocktail"),
        ("What's in a Mojito?", "cocktail"),
    ]

    # Hosting agents to test
    agents_to_test = [
        {
            "name": "Hosting Agent GE2 Staging",
            "url": "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/9013342226205376512/a2a"
        },
    ]

    all_passed = True
    for agent in agents_to_test:
        try:
            passed = await test_agent(agent["url"], agent["name"], test_cases)
            all_passed = all_passed and passed
        except Exception as e:
            logger.error(f"Failed to test {agent['name']}: {e}")
            all_passed = False

    print(f"\n{'='*80}")
    print("OVERALL RESULT")
    print('='*80)
    if all_passed:
        print("✓ All hosting agents passed all tests")
    else:
        print("✗ Some tests failed")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
