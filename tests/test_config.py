# Copyright 2025 Google LLC
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

"""Shared test configuration.

All environment-specific values (project IDs, agent IDs, URLs) are loaded
from environment variables. Hardcoded defaults are intentionally removed
so that tests fail fast when required configuration is missing, rather than
silently running against the wrong environment.

Required environment variables:
    PROJECT_ID: GCP project ID (e.g., "my-project-id")
    PROJECT_NUMBER: GCP project number (e.g., "123456789")

Optional environment variables (with sensible defaults or derived values):
    GOOGLE_CLOUD_REGION / GOOGLE_CLOUD_LOCATION: GCP region (default: us-central1)
    COCKTAIL_AGENT_ID: Reasoning Engine ID for Cocktail Agent
    WEATHER_AGENT_ID: Reasoning Engine ID for Weather Agent
    HOSTING_AGENT_ID: Reasoning Engine ID for Hosting Agent
    CT_MCP_SERVER_URL: Cocktail MCP server URL
    WEA_MCP_SERVER_URL: Weather MCP server URL
    CT_AGENT_URL: Cocktail Agent A2A URL (for hosting agent sub-agents)
    WEA_AGENT_URL: Weather Agent A2A URL (for hosting agent sub-agents)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from multiple possible locations
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.deploy")  # Deployment config
load_dotenv(project_root / "src" / "a2a_agents" / ".env")  # Agent config
load_dotenv()  # Current directory .env

# ---------------------------------------------------------------------------
# Project configuration (required)
# ---------------------------------------------------------------------------
PROJECT_ID = os.environ.get("PROJECT_ID", "")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER", "")
LOCATION = (
    os.environ.get("GOOGLE_CLOUD_REGION")
    or os.environ.get("GOOGLE_CLOUD_LOCATION")
    or "us-central1"
)

# ---------------------------------------------------------------------------
# Agent Engine IDs (optional - tests that need them will skip if missing)
# ---------------------------------------------------------------------------
COCKTAIL_AGENT_ID = os.environ.get("COCKTAIL_AGENT_ID", "")
WEATHER_AGENT_ID = os.environ.get("WEATHER_AGENT_ID", "")
HOSTING_AGENT_ID = os.environ.get("HOSTING_AGENT_ID", "")

# ---------------------------------------------------------------------------
# Derived URLs - constructed from IDs when available
# ---------------------------------------------------------------------------
_AIPLATFORM_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1"


def _agent_a2a_url(agent_id: str) -> str:
    """Build the A2A endpoint URL for an agent."""
    if not PROJECT_NUMBER or not agent_id:
        return ""
    resource = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}"
    return f"{_AIPLATFORM_BASE}/{resource}/a2a"


def _agent_resource_name(agent_id: str) -> str:
    """Build the full resource name for an agent."""
    if not PROJECT_NUMBER or not agent_id:
        return ""
    return f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}"


# A2A endpoint URLs
COCKTAIL_AGENT_URL = os.environ.get("COCKTAIL_AGENT_URL") or _agent_a2a_url(COCKTAIL_AGENT_ID)
WEATHER_AGENT_URL = os.environ.get("WEATHER_AGENT_URL") or _agent_a2a_url(WEATHER_AGENT_ID)
HOSTING_AGENT_URL = os.environ.get("HOSTING_AGENT_URL") or _agent_a2a_url(HOSTING_AGENT_ID)

# Resource names (for agent_engines API)
COCKTAIL_AGENT_RESOURCE_NAME = _agent_resource_name(COCKTAIL_AGENT_ID)
WEATHER_AGENT_RESOURCE_NAME = _agent_resource_name(WEATHER_AGENT_ID)
HOSTING_AGENT_RESOURCE_NAME = _agent_resource_name(HOSTING_AGENT_ID)

# Sub-agent URLs used by the Hosting Agent
CT_AGENT_URL = os.environ.get("CT_AGENT_URL") or COCKTAIL_AGENT_URL
WEA_AGENT_URL = os.environ.get("WEA_AGENT_URL") or WEATHER_AGENT_URL

# ---------------------------------------------------------------------------
# MCP Server URLs
# ---------------------------------------------------------------------------
CT_MCP_SERVER_URL = os.environ.get("CT_MCP_SERVER_URL", "")
WEA_MCP_SERVER_URL = os.environ.get("WEA_MCP_SERVER_URL", "")

# Base URLs (without /mcp/ path) for OIDC audience
CT_MCP_BASE_URL = CT_MCP_SERVER_URL.rstrip("/").removesuffix("/mcp") if CT_MCP_SERVER_URL else ""
WEA_MCP_BASE_URL = WEA_MCP_SERVER_URL.rstrip("/").removesuffix("/mcp") if WEA_MCP_SERVER_URL else ""

# ---------------------------------------------------------------------------
# Frontend URL
# ---------------------------------------------------------------------------
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    f"https://a2a-frontend-ge2-{PROJECT_NUMBER}.{LOCATION}.run.app" if PROJECT_NUMBER else "",
)

# ---------------------------------------------------------------------------
# Test defaults
# ---------------------------------------------------------------------------
DEFAULT_USER_ID = "test_user"
DEFAULT_TIMEOUT = 90.0  # seconds
DEFAULT_POLL_ATTEMPTS = 45
POLL_INTERVAL = 2  # seconds
