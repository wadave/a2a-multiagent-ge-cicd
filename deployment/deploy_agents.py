# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Deploy all A2A agents to Vertex AI Agent Engine.

This script deploys the Cocktail, Weather, and Hosting agents sequentially.
It uses the A2aAgent wrapper from vertexai.preview.reasoning_engines, which
handles A2A protocol translation automatically.

Environment variables:
    PROJECT_ID: GCP project ID for deployment
    GOOGLE_CLOUD_REGION: GCP region (default: us-central1)
    APP_SERVICE_ACCOUNT: Service account email for the agents
    CT_MCP_SERVER_URL: Cocktail MCP server URL
    WEA_MCP_SERVER_URL: Weather MCP server URL
    COMMIT_SHA: Git commit SHA for change detection
    DISPLAY_NAME_SUFFIX: Environment suffix (e.g., "Staging", "Prod")
    BUCKET_NAME: GCS bucket for staging (default: {PROJECT_ID}-bucket)
"""

import logging
import os
import sys

# Add src to path so that a2a_agents are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import vertexai
from dotenv import load_dotenv
from google.genai import types
from vertexai.preview.reasoning_engines import A2aAgent

from a2a_agents.cocktail_agent.cocktail_agent_card import cocktail_agent_card
from a2a_agents.cocktail_agent.cocktail_agent_executor import CocktailAgentExecutor
from a2a_agents.hosting_agent.agent_executor import HostingAgentExecutor
from a2a_agents.hosting_agent.hosting_agent_card import hosting_agent_card
from a2a_agents.weather_agent.weather_agent_card import weather_agent_card
from a2a_agents.weather_agent.weather_agent_executor import WeatherAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_existing_agent(client, display_name):
    """Find an existing agent by display name.

    Args:
        client: Vertex AI client
        display_name: Agent display name to search for

    Returns:
        The existing agent object, or None if not found
    """
    try:
        for agent in client.agent_engines.list():
            if agent.display_name == display_name:
                return agent
    except Exception as e:
        logger.warning(f"Failed to list existing agents: {e}")
    return None


def deploy_agent(
    client,
    display_name,
    agent_card,
    executor_builder,
    project_id,
    location,
    service_account,
    bucket_name,
    requirements_file,
    extra_env_vars,
    commit_sha,
):
    """Deploy a single agent to Vertex AI Agent Engine.

    Checks for existing deployment with matching COMMIT_SHA and skips if found.

    Args:
        client: Vertex AI client
        display_name: Display name for the agent
        agent_card: A2A agent card definition
        executor_builder: Agent executor class
        project_id: GCP project ID
        location: GCP region
        service_account: Service account email
        bucket_name: GCS staging bucket name
        requirements_file: Path to requirements.txt
        extra_env_vars: Additional env vars for the agent
        commit_sha: Git commit SHA for change detection

    Returns:
        The agent resource name (e.g., projects/.../locations/.../reasoningEngines/...)
    """
    # Check if agent already deployed with this COMMIT_SHA
    if commit_sha:
        existing = find_existing_agent(client, display_name)
        if existing:
            existing_sha = None
            # Try to get COMMIT_SHA from existing agent's env vars
            try:
                if hasattr(existing, "env_vars") and existing.env_vars:
                    existing_sha = existing.env_vars.get("COMMIT_SHA")
            except Exception:
                pass

            if existing_sha == commit_sha:
                agent_name = existing.api_resource.name
                logger.info(
                    f"Agent '{display_name}' already deployed with "
                    f"COMMIT_SHA={commit_sha}, skipping. Resource: {agent_name}"
                )
                return agent_name

    agent = A2aAgent(agent_card=agent_card, agent_executor_builder=executor_builder)

    env_vars = {
        "PROJECT_ID": project_id,
        "LOCATION": location,
        "BUCKET": bucket_name,
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "COMMIT_SHA": commit_sha or "",
    }
    env_vars.update(extra_env_vars)

    # Vertex AI rejects empty string env var values
    env_vars = {k: v for k, v in env_vars.items() if v}

    logger.info(f"Deploying '{display_name}' to Agent Engine...")

    remote_agent = client.agent_engines.create(
        agent=agent,
        config={
            "display_name": display_name,
            "description": agent.agent_card.description,
            "service_account": service_account,
            "requirements_file": requirements_file,
            "http_options": {
                "base_url": f"https://{location}-aiplatform.googleapis.com",
                "api_version": "v1beta1",
            },
            "staging_bucket": f"gs://{bucket_name}",
            "env_vars": env_vars,
            "extra_packages": ["a2a_agents"],
        },
    )
    agent_name = remote_agent.api_resource.name
    logger.info(f"Deployed '{display_name}' successfully: {agent_name}")
    return agent_name


def main():
    """Deploy all agents: Cocktail, Weather, then Hosting."""
    # Change working directory to src/ so extra_packages path resolves correctly
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    os.chdir(src_dir)
    logger.info(f"Changed working directory to {src_dir}")

    load_dotenv()

    project_id = os.environ.get("PROJECT_ID")
    location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
    service_account = os.environ.get("APP_SERVICE_ACCOUNT")
    bucket_name = os.environ.get("BUCKET_NAME", f"{project_id}-bucket")
    commit_sha = os.environ.get("COMMIT_SHA", "")
    display_name_suffix = os.environ.get("DISPLAY_NAME_SUFFIX", "Staging")
    requirements_file = os.environ.get("REQUIREMENTS_FILE", "requirements.txt")

    ct_mcp_url = os.environ.get("CT_MCP_SERVER_URL")
    wea_mcp_url = os.environ.get("WEA_MCP_SERVER_URL")

    if not project_id:
        logger.error("PROJECT_ID must be set in environment.")
        sys.exit(1)

    if not service_account:
        logger.error("APP_SERVICE_ACCOUNT must be set in environment.")
        sys.exit(1)

    if not ct_mcp_url or not wea_mcp_url:
        logger.error("CT_MCP_SERVER_URL and WEA_MCP_SERVER_URL must be set.")
        sys.exit(1)

    vertexai.init(
        project=project_id, location=location, staging_bucket=f"gs://{bucket_name}"
    )
    client = vertexai.Client(
        project=project_id,
        location=location,
        http_options=types.HttpOptions(
            api_version="v1beta1",
            base_url=f"https://{location}-aiplatform.googleapis.com/",
        ),
    )

    # --- Deploy Cocktail Agent ---
    try:
        ct_agent_name = deploy_agent(
            client=client,
            display_name=f"Cocktail Agent GE {display_name_suffix}",
            agent_card=cocktail_agent_card,
            executor_builder=CocktailAgentExecutor,
            project_id=project_id,
            location=location,
            service_account=service_account,
            bucket_name=bucket_name,
            requirements_file=requirements_file,
            extra_env_vars={"CT_MCP_SERVER_URL": ct_mcp_url},
            commit_sha=commit_sha,
        )
    except Exception as e:
        logger.error(f"Failed to deploy Cocktail Agent: {e}")
        sys.exit(1)

    # --- Deploy Weather Agent ---
    try:
        wea_agent_name = deploy_agent(
            client=client,
            display_name=f"Weather Agent GE {display_name_suffix}",
            agent_card=weather_agent_card,
            executor_builder=WeatherAgentExecutor,
            project_id=project_id,
            location=location,
            service_account=service_account,
            bucket_name=bucket_name,
            requirements_file=requirements_file,
            extra_env_vars={"WEA_MCP_SERVER_URL": wea_mcp_url},
            commit_sha=commit_sha,
        )
    except Exception as e:
        logger.error(f"Failed to deploy Weather Agent: {e}")
        sys.exit(1)

    # Build A2A endpoint URLs for the sub-agents
    ct_agent_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{ct_agent_name}/environments/default"
    wea_agent_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{wea_agent_name}/environments/default"

    # --- Deploy Hosting Agent ---
    try:
        host_agent_name = deploy_agent(
            client=client,
            display_name=f"Hosting Agent GE {display_name_suffix}",
            agent_card=hosting_agent_card,
            executor_builder=HostingAgentExecutor,
            project_id=project_id,
            location=location,
            service_account=service_account,
            bucket_name=bucket_name,
            requirements_file=requirements_file,
            extra_env_vars={
                "CT_AGENT_URL": ct_agent_url,
                "WEA_AGENT_URL": wea_agent_url,
            },
            commit_sha=commit_sha,
        )
    except Exception as e:
        logger.error(f"Failed to deploy Hosting Agent: {e}")
        sys.exit(1)

    logger.info("All agents deployed successfully.")

    # Write hosting agent ID to workspace file for downstream Cloud Build steps
    output_file = os.environ.get(
        "HOSTING_AGENT_OUTPUT", "/workspace/hosting_agent_id.txt"
    )
    try:
        with open(output_file, "w") as f:
            f.write(host_agent_name)
        logger.info(f"Wrote hosting agent ID to {output_file}")
    except OSError as e:
        logger.warning(f"Could not write hosting agent ID to {output_file}: {e}")
        # Print to stdout as fallback
        print(f"HOSTING_AGENT_ID={host_agent_name}")


if __name__ == "__main__":
    main()
