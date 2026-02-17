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

"""Shared test configuration and utilities."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from multiple possible locations
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.deploy")  # Deployment config
load_dotenv(project_root / "src" / "a2a_agents" / ".env")  # Agent config
load_dotenv()  # Current directory .env

# Project configuration
PROJECT_ID = os.getenv("PROJECT_ID", "dw-genai-dev")
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER", "496235138247")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Agent IDs (from environment or defaults)
COCKTAIL_AGENT_ID = os.getenv("COCKTAIL_AGENT_ID", "7385853910864363520")
WEATHER_AGENT_ID = os.getenv("WEATHER_AGENT_ID", "3972230946433794048")
HOSTING_AGENT_ID = os.getenv("HOSTING_AGENT_ID", "6246548758255894528")

# Agent URLs (constructed from IDs)
COCKTAIL_AGENT_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{COCKTAIL_AGENT_ID}/a2a"
WEATHER_AGENT_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{WEATHER_AGENT_ID}/a2a"
HOSTING_AGENT_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{HOSTING_AGENT_ID}"

# MCP Server URLs
CT_MCP_SERVER_URL = os.getenv("CT_MCP_SERVER_URL", "https://cocktail-mcp-ge-staging-lxo6yz2aha-uc.a.run.app/mcp/")
WEA_MCP_SERVER_URL = os.getenv("WEA_MCP_SERVER_URL", "https://weather-mcp-ge-staging-lxo6yz2aha-uc.a.run.app/mcp/")

# Test configuration
DEFAULT_USER_ID = "test_user"
DEFAULT_TIMEOUT = 90.0  # seconds
DEFAULT_POLL_ATTEMPTS = 45
POLL_INTERVAL = 2  # seconds
