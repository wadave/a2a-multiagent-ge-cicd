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
    DISPLAY_NAME_SUFFIX: Environment suffix (e.g., "Staging", "Prod")
    BUCKET_NAME: GCS bucket for staging (default: {PROJECT_ID}-bucket)
    REQUIREMENTS_FILE: Path to requirements.txt (default: requirements.txt)
"""

import logging
import os
import sys
import time

# Add src to path so that a2a_agents are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import vertexai
from dotenv import load_dotenv
from google.genai import types
from vertexai.preview.reasoning_engines import A2aAgent

from a2a_agents.cocktail_agent.cocktail_agent_card import cocktail_agent_card
from a2a_agents.cocktail_agent.cocktail_agent_executor import CocktailAgentExecutor
from a2a_agents.hosting_agent.adk_agent import create_hosting_agent
from a2a_agents.hosting_agent.agent_executor import HostingAgentExecutor
from a2a_agents.hosting_agent.hosting_agent_card import hosting_agent_card
from a2a_agents.weather_agent.weather_agent_card import weather_agent_card
from a2a_agents.weather_agent.weather_agent_executor import WeatherAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_existing_agents(client):
    """List all existing agents and return a dict keyed by display name."""
    agents = {}
    try:
        for agent in client.agent_engines.list():
            name = agent.api_resource.display_name
            if name:
                agents[name] = agent.api_resource.name
    except Exception as e:
        logger.warning(f"Failed to list existing agents: {e}")
    return agents


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
    existing_agents,
):
    """Deploy an A2A agent using the A2aAgent template."""
    if display_name in existing_agents:
        agent_name = existing_agents[display_name]
        logger.info(f"Agent '{display_name}' already exists: {agent_name}")
        return agent_name

    a2a_agent = A2aAgent(
        agent_card=agent_card, agent_executor_builder=executor_builder
    )

    env_vars = {
        "PROJECT_ID": project_id,
        "LOCATION": location,
        "BUCKET": bucket_name,
    }
    env_vars.update(extra_env_vars)
    env_vars = {k: v for k, v in env_vars.items() if v}

    logger.info(f"Deploying '{display_name}' (A2A Template)...")

    config = {
        "display_name": display_name,
        "description": a2a_agent.agent_card.description,
        "service_account": service_account,
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]>=1.112.0",
            "a2a-sdk >= 0.3.4",
            "pydantic>=2.11.9",
            "cloudpickle>=3.1.1",
            "google-auth-oauthlib>=1.2.2",
            "google-auth[openid]>=2.40.3",
            "google-genai>=1.36.0",
        ],
        "http_options": {
            "base_url": f"https://{location}-aiplatform.googleapis.com",
            "api_version": "v1beta1",
        },
        "staging_bucket": f"gs://{bucket_name}",
        "env_vars": env_vars,
        "extra_packages": ["a2a_agents"],
    }
    
    remote_agent = client.agent_engines.create(agent=a2a_agent, config=config)
    agent_name = remote_agent.api_resource.name
    logger.info(f"Deployed '{display_name}' successfully: {agent_name}")
    return agent_name


def deploy_adk_agent(
    client,
    display_name,
    agent_factory,
    project_id,
    location,
    service_account,
    bucket_name,
    requirements_file,
    extra_env_vars,
    existing_agents,
):
    """Deploy an ADK agent to Vertex AI Agent Engine."""
    if display_name in existing_agents:
        agent_name = existing_agents[display_name]
        logger.info(f"Agent '{display_name}' already exists: {agent_name}")
        return agent_name

    # Set env vars temporarily so the factory picks them up if needed
    original_env = os.environ.copy()
    os.environ.update(extra_env_vars)
    
    try:
        agent_engine = agent_factory()
    finally:
        os.environ.clear()
        os.environ.update(original_env)

    env_vars = {
        "PROJECT_ID": project_id,
        "LOCATION": location,
        "BUCKET": bucket_name,
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
    }
    env_vars.update(extra_env_vars)
    env_vars = {k: v for k, v in env_vars.items() if v}

    logger.info(f"Deploying '{display_name}' (ADK Model)...")

    config = {
        "display_name": display_name,
        "description": agent_engine.description,
        "service_account": service_account,
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]>=1.112.0",
            "a2a-sdk >= 0.3.4",
            "pydantic>=2.11.9",
            "cloudpickle>=3.1.1",
            "google-auth-oauthlib>=1.2.2",
            "google-auth[openid]>=2.40.3",
            "google-genai>=1.36.0",
        ],
        "http_options": {
            "base_url": f"https://{location}-aiplatform.googleapis.com",
            "api_version": "v1beta1",
        },
        "staging_bucket": f"gs://{bucket_name}",
        "env_vars": env_vars,
        "extra_packages": ["a2a_agents"],
    }

    remote_agent = client.agent_engines.create(agent_engine=agent_engine, config=config)
    agent_name = remote_agent.api_resource.name
    logger.info(f"Deployed '{display_name}' successfully: {agent_name}")
    return agent_name


def main():
    """Deploy all agents."""
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    os.chdir(src_dir)

    load_dotenv()

    project_id = os.environ.get("PROJECT_ID")
    location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
    service_account = os.environ.get("APP_SERVICE_ACCOUNT")
    bucket_name = os.environ.get("BUCKET_NAME", f"{project_id}-bucket")
    display_name_suffix = os.environ.get("DISPLAY_NAME_SUFFIX", "Staging")
    requirements_file = os.environ.get("REQUIREMENTS_FILE", "requirements.txt")

    ct_mcp_url = os.environ.get("CT_MCP_SERVER_URL")
    wea_mcp_url = os.environ.get("WEA_MCP_SERVER_URL")

    if not project_id or not service_account or not ct_mcp_url or not wea_mcp_url:
        logger.error("Missing required environment variables (PROJECT_ID, APP_SERVICE_ACCOUNT, etc.)")
        sys.exit(1)

    vertexai.init(project=project_id, location=location, staging_bucket=f"gs://{bucket_name}")
    client = vertexai.Client(
        project=project_id,
        location=location,
        http_options=types.HttpOptions(
            api_version="v1beta1",
            base_url=f"https://{location}-aiplatform.googleapis.com/",
        ),
    )

    existing_agents = list_existing_agents(client)

    # --- Deploy Cocktail Agent ---
    ct_agent_name = deploy_agent(
        client=client,
        display_name=f"Cocktail Agent GE2 {display_name_suffix}",
        agent_card=cocktail_agent_card,
        executor_builder=CocktailAgentExecutor,
        project_id=project_id,
        location=location,
        service_account=service_account,
        bucket_name=bucket_name,
        requirements_file=requirements_file,
        extra_env_vars={"CT_MCP_SERVER_URL": ct_mcp_url},
        existing_agents=existing_agents,
    )

    # --- Deploy Weather Agent ---
    wea_agent_name = deploy_agent(
        client=client,
        display_name=f"Weather Agent GE2 {display_name_suffix}",
        agent_card=weather_agent_card,
        executor_builder=WeatherAgentExecutor,
        project_id=project_id,
        location=location,
        service_account=service_account,
        bucket_name=bucket_name,
        requirements_file=requirements_file,
        extra_env_vars={"WEA_MCP_SERVER_URL": wea_mcp_url},
        existing_agents=existing_agents,
    )

    # URLs for Hosting Agent
    ct_agent_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{ct_agent_name}/a2a"
    wea_agent_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{wea_agent_name}/a2a"

    # --- Deploy Hosting Agent ---
    host_agent_name = deploy_adk_agent(
        client=client,
        display_name=f"Hosting Agent GE2 {display_name_suffix}",
        agent_factory=create_hosting_agent,
        project_id=project_id,
        location=location,
        service_account=service_account,
        bucket_name=bucket_name,
        requirements_file=requirements_file,
        extra_env_vars={
            "CT_AGENT_URL": ct_agent_url,
            "WEA_AGENT_URL": wea_agent_url,
        },
        existing_agents=existing_agents,
    )

    logger.info(f"All agents deployed. Hosting Agent: {host_agent_name}")

    # Write hosting agent ID for CI/CD pipeline (frontend deployment reads this)
    hosting_agent_id_path = os.environ.get(
        "HOSTING_AGENT_ID_FILE", "/workspace/hosting_agent_id.txt"
    )
    try:
        with open(hosting_agent_id_path, "w") as f:
            f.write(host_agent_name)
        logger.info(f"Wrote hosting agent ID to {hosting_agent_id_path}")
    except OSError:
        logger.warning(f"Could not write hosting agent ID to {hosting_agent_id_path}")


if __name__ == "__main__":
    main()
