import argparse
import json
import logging
import subprocess
import sys

import requests

logging.getLogger().setLevel(logging.INFO)


def get_bearer_token() -> str:
    """Get the gcloud access token."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting gcloud token: {e}")
        logging.error(
            "Please ensure you are authenticated or running in an environment "
            "with default credentials."
        )
        sys.exit(1)


def get_base_url(location: str) -> str:
    """Build the Discovery Engine base URL for the given location."""
    return f"https://{location}-discoveryengine.googleapis.com"


def get_agents_url(project_number: str, location: str, app_id: str) -> str:
    """Build the agents collection URL."""
    base_url = get_base_url(location)
    return (
        f"{base_url}/v1alpha/projects/{project_number}/"
        f"locations/{location}/collections/default_collection/"
        f"engines/{app_id}/assistants/default_assistant/agents"
    )


def get_headers(project_number: str) -> dict:
    """Build request headers with auth token."""
    bearer_token = get_bearer_token()
    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_number,
    }


def list_registered_agents(
    project_number: str,
    location: str,
    app_id: str,
) -> list[dict]:
    """List all agents registered in Agentspace.

    Returns:
        List of agent dicts, or empty list on error.
    """
    url = get_agents_url(project_number, location, app_id)
    headers = get_headers(project_number)

    logging.info(f"Listing registered agents from {url}")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        agents = data.get("agents", [])
        logging.info(f"Found {len(agents)} registered agent(s)")
        return agents
    else:
        logging.warning(
            f"Failed to list agents (status {response.status_code}): "
            f"{response.text}"
        )
        return []


def find_agent_by_display_name(
    agents: list[dict], display_name: str
) -> dict | None:
    """Find a registered agent by its displayName."""
    for agent in agents:
        if agent.get("displayName") == display_name:
            return agent
    return None


def update_agent(
    project_number: str,
    location: str,
    app_id: str,
    agent_id: str,
    payload: dict,
) -> dict | None:
    """Update an existing agent registration via PATCH."""
    url = f"{get_agents_url(project_number, location, app_id)}/{agent_id}"
    headers = get_headers(project_number)

    logging.info(f"Updating agent {agent_id}...")
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        logging.info("Agent updated successfully!")
        return response.json()
    else:
        logging.error(
            f"Update failed (status {response.status_code}): {response.text}"
        )
        response.raise_for_status()


def register_agent(
    project_number: str,
    location: str,
    app_id: str,
    payload: dict,
) -> dict | None:
    """Register a new agent via POST."""
    url = get_agents_url(project_number, location, app_id)
    headers = get_headers(project_number)

    logging.info(f"Registering agent to Gemini Enterprise...")
    logging.info(f"API Endpoint: {url}")
    logging.info(f"Display Name: {payload.get('displayName')}")

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        logging.info("Agent registered successfully!")
        return response.json()
    else:
        logging.error(
            f"Registration failed (status {response.status_code}): "
            f"{response.text}"
        )
        response.raise_for_status()


def main():
    parser = argparse.ArgumentParser(
        description="Register or update an A2A agent in Gemini Enterprise Agentspace"
    )
    parser.add_argument(
        "--project-number", required=True, help="GCP Project Number"
    )
    parser.add_argument(
        "--app-id",
        required=True,
        help="Gemini Enterprise Application ID (AS_APP)",
    )
    parser.add_argument(
        "--agent-url", required=True, help="Agent Engine URL to register"
    )
    parser.add_argument(
        "--agent-name", default="a2a-agent", help="Internal name of the agent"
    )
    parser.add_argument(
        "--display-name", default="A2A Agent", help="Display name"
    )
    parser.add_argument(
        "--description",
        default="Agent registered via CI/CD",
        help="Agent description",
    )
    parser.add_argument(
        "--location",
        default="global",
        help="Endpoint location (global, us, eu)",
    )
    parser.add_argument(
        "--auth-id", help="OAuth Authorization ID (AUTH_ID)"
    )

    args = parser.parse_args()

    # Build the agent card per A2A protocol spec
    agent_card = {
        "protocolVersion": "v1.0",
        "name": args.display_name,
        "description": args.description,
        "url": args.agent_url,
        "version": "1.0.0",
        "capabilities": {},
        "skills": [
            {
                "id": "question_answer",
                "name": "Q&A Agent",
                "description": "Answer questions about weather and cocktails",
                "tags": ["Question-Answer"],
            }
        ],
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
    }

    payload = {
        "name": args.agent_name,
        "displayName": args.display_name,
        "description": args.description,
        "a2aAgentDefinition": {
            "jsonAgentCard": json.dumps(agent_card),
        },
    }

    if args.auth_id:
        payload["authorizationConfig"] = {
            "agentAuthorization": (
                f"projects/{args.project_number}/locations/{args.location}/"
                f"authorizations/{args.auth_id}"
            )
        }

    # Check if agent already exists - update instead of creating duplicate
    existing_agents = list_registered_agents(
        args.project_number, args.location, args.app_id
    )
    existing = find_agent_by_display_name(existing_agents, args.display_name)

    if existing:
        # Extract agent ID from resource name (last path segment)
        agent_resource_name = existing.get("name", "")
        agent_id = agent_resource_name.rsplit("/", 1)[-1]
        logging.info(
            f"Agent '{args.display_name}' already registered "
            f"(id={agent_id}), updating..."
        )
        result = update_agent(
            project_number=args.project_number,
            location=args.location,
            app_id=args.app_id,
            agent_id=agent_id,
            payload=payload,
        )
    else:
        result = register_agent(
            project_number=args.project_number,
            location=args.location,
            app_id=args.app_id,
            payload=payload,
        )

    logging.info(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
