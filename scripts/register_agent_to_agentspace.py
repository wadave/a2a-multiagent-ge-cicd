import argparse
import json
import logging
import os
import requests
import subprocess
import sys

# Set logging
logging.getLogger().setLevel(logging.INFO)

def get_bearer_token() -> str:
    """Get the gcloud access token."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting gcloud token: {e}")
        logging.error("Please ensure you are authenticated or running in an environment with default credentials.")
        sys.exit(1)


def register_agent_on_gemini_enterprise(
    project_number: str,
    app_id: str,
    agent_card_json: str,
    agent_name: str,
    display_name: str,
    description: str,
    agent_authorization: str | None = None,
) -> dict | None:
    """Register an Agent Engine to Gemini Enterprise using the Discovery API."""
    
    # Defaults base_url to global
    base_url = "https://discoveryengine.googleapis.com"
    location = "global"

    api_endpoint = (
        f"{base_url}/v1alpha/projects/{project_number}/"
        f"locations/{location}/collections/default_collection/engines/{app_id}/"
        f"assistants/default_assistant/agents"
    )

    payload = {
        "name": agent_name,
        "displayName": display_name,
        "description": description,
        "a2aAgentDefinition": {
            "jsonAgentCard": agent_card_json
        },
    }

    if agent_authorization:
        payload["authorization_config"] = {
            "agent_authorization": agent_authorization
        }

    bearer_token = get_bearer_token()

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_number,
    }

    logging.info(f"Registering agent to Gemini Enterprise...")
    logging.info(f"API Endpoint: {api_endpoint}")
    logging.info(f"Display Name: {display_name}")

    response = requests.post(api_endpoint, headers=headers, json=payload)

    if response.status_code == 200:
        logging.info("V Agent registered successfully!")
        return response.json()
    else:
        logging.error(f"X Registration failed with status code: {response.status_code}")
        logging.error(f"Response: {response.text}")
        response.raise_for_status()


def main():
    parser = argparse.ArgumentParser(description="Register Agent to Agentspace")
    parser.add_argument("--project-number", required=True, help="GCP Project Number")
    parser.add_argument("--app-id", required=True, help="Gemini Enterprise Application ID (AS_APP)")
    parser.add_argument("--agent-url", required=True, help="Agent Engine URL to register")
    parser.add_argument("--agent-name", default="A2A", help="Internal Name of the agent")
    parser.add_argument("--display-name", default="A2A Agent", help="Display Name")
    parser.add_argument("--description", default="Agent registered via CI/CD", help="Agent Description")
    parser.add_argument("--auth-id", help="OAuth Authorization ID (AUTH_ID)")
    
    args = parser.parse_args()

    agent_card = {
        "url": args.agent_url,
        "name": "A2A_Test_Agent",
        "preferredTransport": "HTTP+JSON",
        "description": args.description,
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "description": "You're an export of weather and cocktail, answer questions regarding weather and cocktail",
                "examples": [
                    "Weather in LA, CA",
                    "What are ingrediants formargarita?"
                ],
                "id": "question_answer",
                "name": "Q&A Agent",
                "tags": [
                    "Question-Answer"
                ]
            }
        ],
        "version": "1.0.0",
        "supportsAuthenticatedExtendedCard": True,
        "protocolVersion": "0.3.0"
    }

    compact_card = json.dumps(agent_card)

    agent_authorization = None
    if args.auth_id:
         agent_authorization = f"projects/{args.project_number}/locations/global/authorizations/{args.auth_id}"

    result = register_agent_on_gemini_enterprise(
        project_number=args.project_number,
        app_id=args.app_id,
        agent_card_json=compact_card,
        agent_name=args.agent_name,
        display_name=args.display_name,
        description=args.description,
        agent_authorization=agent_authorization
    )
    
    logging.info(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
