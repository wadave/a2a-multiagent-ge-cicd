# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Author: Dave Wang

"""Shared test utilities."""
import asyncio
import subprocess

import httpx


def get_gcloud_token() -> str:
    """Get gcloud access token for authentication."""
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


async def test_a2a_agent(
    agent_id: str,
    agent_name: str,
    query: str,
    project_number: str,
    location: str,
    timeout: float = 90.0,
    poll_attempts: int = 45,
    poll_interval: int = 2,
) -> tuple[bool, str | None]:
    """
    Test an A2A agent via the A2A protocol.

    Args:
        agent_id: The reasoning engine ID
        agent_name: Human-readable name for logging
        query: The query to send
        project_number: GCP project number
        location: GCP location
        timeout: HTTP timeout in seconds
        poll_attempts: Number of polling attempts
        poll_interval: Seconds between polls

    Returns:
        Tuple of (success, response_text)
    """
    print(f"\n{'='*80}")
    print(f"Testing: {agent_name}")
    print(f"Agent ID: {agent_id}")
    print(f"Query: {query}")
    print('='*80)

    resource_name = f"projects/{project_number}/locations/{location}/reasoningEngines/{agent_id}"
    base_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{resource_name}/a2a"

    token = get_gcloud_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Send message
        print("\n--- Sending Message ---")
        msg_url = f"{base_url}/v1/message:send"
        message_data = {
            "message": {
                "messageId": f"msg-test-{agent_id[:8]}",
                "role": "1",
                "content": [{"text": query}],
            },
        }

        resp = await client.post(msg_url, headers=headers, json=message_data)
        if resp.status_code != 200:
            print(f"✗ Failed to send message: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return False, None

        task_resp = resp.json()
        task_id = task_resp.get("task", {}).get("id")
        if not task_id:
            print("✗ No task ID in response")
            return False, None

        print(f"✓ Task created: {task_id}")

        # Poll for result
        print("\n--- Polling for Result ---")
        task_url = f"{base_url}/v1/tasks/{task_id}"

        for i in range(poll_attempts):
            resp = await client.get(task_url, headers=headers, params={"history_length": 1})

            if resp.status_code != 200:
                print(f"  Poll {i+1}: Failed with {resp.status_code}, retrying...")
                await asyncio.sleep(poll_interval)
                continue

            task_data = resp.json()
            state = task_data.get("status", {}).get("state")
            print(f"  Poll {i+1}: State = {state}")

            if state == "TASK_STATE_COMPLETED":
                artifacts = task_data.get("artifacts", [])
                response_text = ""

                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if "text" in part:
                            response_text += part["text"] + "\n"

                if response_text:
                    print("\n✓ Response received:")
                    print("-" * 80)
                    print(response_text[:500])
                    if len(response_text) > 500:
                        print(f"... (truncated, total length: {len(response_text)})")
                    print("-" * 80)
                    return True, response_text
                else:
                    print("⚠️  Task completed but no text response")
                    return False, None

            elif state == "TASK_STATE_FAILED":
                print("✗ Task failed")
                return False, None

            await asyncio.sleep(poll_interval)

        print("✗ Timeout waiting for response")
        return False, None


async def test_adk_agent(
    agent_resource_name: str,
    query: str,
    project_id: str,
    location: str,
    user_id: str = "test_user",
) -> tuple[bool, str | None]:
    """
    Test an ADK agent via the agent_engines API.

    Args:
        agent_resource_name: Full resource name of the agent
        query: The query to send
        project_id: GCP project ID
        location: GCP location
        user_id: User ID for the session

    Returns:
        Tuple of (success, response_text)
    """
    import vertexai
    from vertexai import agent_engines

    print(f"\n{'='*80}")
    print("Testing ADK Agent")
    print(f"Resource: {agent_resource_name}")
    print(f"Query: {query}")
    print('='*80)

    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

    # Get the remote agent
    remote_agent = agent_engines.get(agent_resource_name)
    print(f"✓ Connected to agent: {remote_agent.display_name}")

    # Create a session
    session = await remote_agent.async_create_session(user_id=user_id)
    session_id = session["id"] if isinstance(session, dict) else session.id
    print(f"✓ Session created: {session_id}")

    # Stream query
    events = []
    async for event in remote_agent.async_stream_query(
        user_id=user_id,
        session_id=session_id,
        message=query,
    ):
        events.append(event)

    # Extract final text response
    final_text_responses = [
        e for e in events
        if e.get("content", {}).get("parts", [{}])[0].get("text")
        and not e.get("content", {}).get("parts", [{}])[0].get("function_call")
    ]

    if final_text_responses:
        response_text = final_text_responses[0]["content"]["parts"][0]["text"]
        print("\n✓ Response received:")
        print("-" * 80)
        print(response_text[:500])
        if len(response_text) > 500:
            print(f"... (truncated, total length: {len(response_text)})")
        print("-" * 80)
        return True, response_text
    else:
        print("\n✗ No text response received")
        return False, None


def print_test_summary(results: list[tuple[str, bool]]) -> bool:
    """
    Print test summary and return overall success.

    Args:
        results: List of (test_name, passed) tuples

    Returns:
        True if all tests passed
    """
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*80)

    return all_passed
