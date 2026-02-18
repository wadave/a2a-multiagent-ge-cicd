import asyncio
import os
import vertexai
from google.genai import types
import httpx
import subprocess
import json
import time

# TODO: Replace with actual resource name after deployment
REMOTE_AGENT_NAME = os.environ.get("REMOTE_AGENT_NAME")

PROJECT_ID = "dw-genai-dev"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

def get_gcloud_token():
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

async def test_remote_agent():
    print(f"Connecting to remote agent: {REMOTE_AGENT_NAME}")
    
    # Construct A2A endpoint URL
    # Format: https://{LOCATION}-aiplatform.googleapis.com/v1beta1/{RESOURCE_NAME}/a2a
    base_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/{REMOTE_AGENT_NAME}/a2a"
    print(f"Base URL: {base_url}")

    token = get_gcloud_token()
    if not token:
        print("Failed to get token")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as http_client:
        # Get card
        print("\n--- Getting Remote Agent Card ---")
        card_url = f"{base_url}/v1/card"
        print(f"GET {card_url}")
        resp = await http_client.get(card_url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to get card: {resp.status_code} {resp.text}")
            return
        
        card = resp.json()
        print(f"Agent: {card.get('name')}")
        print(f"URL: {card.get('url')}")

        # Update base_url from card if available to ensure consistency (Project ID vs Number)
        if card.get('url'):
            base_url = card.get('url')
            print(f"Updated Base URL: {base_url}")

        # Send message
        print("\n--- Sending Message ---")
        msg_url = f"{base_url}/v1/message:send"
        message_data = {
            "message": {
                "messageId": f"msg-{os.urandom(8).hex()}",
                "role": "1", # User
                "content": [{"text": "weather in San Francisco?"}],
            },
        }
        print(f"POST {msg_url}")
        resp = await http_client.post(msg_url, headers=headers, json=message_data)
        if resp.status_code != 200:
            print(f"Failed to send message: {resp.status_code} {resp.text}")
            return
            
        task_resp = resp.json()
        task_id = task_resp.get("task", {}).get("id")
        if not task_id:
            print(f"No task ID in response: {task_resp}")
            return
            
        print(f"Task started: {task_id}")

        # Poll for result
        print("\n--- Polling for Result ---")
        task_url = f"{base_url}/v1/tasks/{task_id}"
        
        for _ in range(30): # Poll for 60 seconds
            resp = await http_client.get(task_url, headers=headers)
            if resp.status_code != 200:
                print(f"Failed to get task: {resp.status_code} {resp.text}")
                break
            
            task_data = resp.json()
            state = task_data.get("status", {}).get("state")
            print(f"State: {state}")
            
            if state == "TASK_STATE_COMPLETED":
                artifacts = task_data.get("artifacts", [])
                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if "text" in part:
                            print(f"\nAnswer:\n{part['text']}")
                return
            elif state == "TASK_STATE_FAILED":
                print(f"Task Failed: {task_data}")
                return
                
            await asyncio.sleep(2)

if __name__ == "__main__":
    if not REMOTE_AGENT_NAME:
        print("Please set REMOTE_AGENT_NAME environment variable")
    else:
        asyncio.run(test_remote_agent())
